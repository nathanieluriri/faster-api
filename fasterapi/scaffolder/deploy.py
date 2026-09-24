from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

TARGETS = ("vercel", "cloudrun")
TEMPLATE_ROOT = Path(__file__).parent / "templates" / "project_template"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "mongo", "redis", "postgres", "db"}
_SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", "tests", ".vercel", "build", "dist", "site-packages"}
_TRUE = {"1", "true", "yes", "on"}

# Values Cloud Run sets itself and rejects in --env-vars-file.
_CLOUDRUN_RESERVED = {"PORT", "K_SERVICE", "K_REVISION", "K_CONFIGURATION"}

_VERCEL_JSON = {
    "builds": [{"src": "main.py", "use": "@vercel/python"}],
    "routes": [{"src": "/(.*)", "dest": "main.py"}],
}

_VERCEL_IGNORE = """.env
.env.*
!.env.example
.venv
venv
env
__pycache__
tests
uploads
Dockerfile
docker-compose.yml
server_automations
"""

_GCLOUD_IGNORE = """.gcloudignore
.git
.gitignore
.env
.env.*
!.env.example
.venv
venv
env
__pycache__
tests
uploads
.vercel
"""

# Preset values that keep a fresh project within what each platform supports.
_ENV_PRESETS = {
    "vercel": {"ENABLE_SCHEDULER": "false", "EMAIL_QUEUE_ENABLED": "false"},
    "cloudrun": {"ENABLE_SCHEDULER": "false", "EMAIL_QUEUE_ENABLED": "false"},
}


@dataclass
class Finding:
    severity: str
    message: str
    fix: str
    location: str | None = None


def _is_true(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in _TRUE


def _host(value: str | None) -> str | None:
    if not value:
        return None
    if "://" not in value:
        return value.strip().lower()
    try:
        return (urlparse(value).hostname or "").lower() or None
    except ValueError:
        return None


def _is_local(value: str | None) -> bool:
    host = _host(value)
    return host is None or host in _LOCAL_HOSTS


def load_env(project: Path, env_file: str | None = None) -> tuple[dict[str, str], str | None]:
    candidates = [project / env_file] if env_file else [project / ".env", project / ".env.example"]
    for path in candidates:
        if path.exists():
            values = {k: (v or "") for k, v in dotenv_values(path).items()}
            return values, path.name
    return {}, None


def _python_files(project: Path):
    for path in project.rglob("*.py"):
        if not any(part in _SKIP_DIRS for part in path.relative_to(project).parts):
            yield path


def _scan(project: Path, pattern: str, exclude: tuple[str, ...] = ()) -> list[str]:
    regex = re.compile(pattern)
    hits = []
    for path in _python_files(project):
        relative = path.relative_to(project).as_posix()
        if relative in exclude:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if regex.search(line) and not line.lstrip().startswith("#"):
                hits.append(f"{relative}:{number}")
    return hits


def _locations(hits: list[str], limit: int = 3) -> str:
    extra = f" (+{len(hits) - limit} more)" if len(hits) > limit else ""
    return ", ".join(hits[:limit]) + extra


def _check_services(env: dict[str, str], target: str) -> list[Finding]:
    findings = []
    db_type = (env.get("DB_TYPE") or "mongodb").lower()

    if db_type == "mongodb":
        if _is_local(env.get("MONGO_URL")):
            findings.append(Finding(
                "error", "MONGO_URL is empty or points to a local/docker host that won't exist in the cloud.",
                "Use a hosted MongoDB such as MongoDB Atlas (free M0 tier) and set MONGO_URL.",
            ))
    elif db_type in {"postgres", "postgresql", "supabase"}:
        url = env.get("DATABASE_URL")
        if _is_local(url):
            findings.append(Finding(
                "error", "DATABASE_URL is empty or points to a local/docker host that won't exist in the cloud.",
                "Use a hosted Postgres such as Supabase, Neon or Cloud SQL and set DATABASE_URL.",
            ))
        elif target == "vercel" and "supabase" in (_host(url) or "") and urlparse(url).port in (None, 5432):
            findings.append(Finding(
                "warning", "DATABASE_URL uses Supabase's direct connection (port 5432). Serverless functions open "
                "many short-lived connections and can exhaust it.",
                "Use Supabase's transaction pooler connection string (port 6543) and DB_TYPE=supabase.",
            ))
    else:
        findings.append(Finding(
            "error", f"DB_TYPE={db_type} is not supported.",
            "Set DB_TYPE to mongodb, postgres or supabase (see: fasterapi db use --help).",
        ))

    redis_url = env.get("CELERY_BROKER_URL") or env.get("REDIS_URL") or env.get("REDIS_HOST")
    if _is_local(redis_url):
        findings.append(Finding(
            "error", "Redis is not configured or points to a local host. Rate limiting reads Redis on every request, "
            "so every request would fail.",
            "Use a hosted Redis such as Upstash (free tier) or Memorystore and set REDIS_URL.",
        ))

    if not env.get("SECRET_KEY"):
        findings.append(Finding(
            "error", "SECRET_KEY is empty, so JWTs would be signed with a publicly known development key.",
            "Set SECRET_KEY to a long random value, e.g. python -c \"import secrets; print(secrets.token_urlsafe(48))\".",
        ))
    if not env.get("SESSION_SECRET_KEY"):
        findings.append(Finding(
            "error", "SESSION_SECRET_KEY is empty, so session cookies would be signed with a known development key.",
            "Set SESSION_SECRET_KEY to a long random value.",
        ))
    super_admin_password = env.get("SUPER_ADMIN_PASSWORD") or ""
    if super_admin_password and len(super_admin_password) < 12:
        findings.append(Finding(
            "error", "SUPER_ADMIN_PASSWORD is shorter than 12 characters, and it unlocks full admin access.",
            "Use a long random password, or leave SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD empty to disable it.",
        ))
    if (env.get("ENV") or "development").lower() != "production":
        findings.append(Finding(
            "warning", "ENV is not 'production', so production safety checks are skipped.",
            "Set ENV=production for deployed environments.",
        ))
    return findings


def _check_runtime_features(project: Path, env: dict[str, str], target: str) -> list[Finding]:
    findings = []
    serverless = target == "vercel"

    if (env.get("STORAGE_BACKEND") or "local").lower() == "local":
        findings.append(Finding(
            "error" if serverless else "warning",
            "STORAGE_BACKEND=local writes uploads to the container's disk. "
            + ("Vercel's filesystem is read-only apart from /tmp, which is wiped between invocations."
               if serverless else "Cloud Run's disk is in memory and is wiped whenever an instance stops."),
            "Set STORAGE_BACKEND=s3. Any S3-compatible store works: AWS S3, Cloudflare R2, or Google Cloud Storage "
            "with S3_ENDPOINT_URL=https://storage.googleapis.com and HMAC keys.",
        ))

    scheduler_default = not serverless
    scheduler_on = _is_true(env.get("ENABLE_SCHEDULER"), scheduler_default)
    extra_jobs = _scan(project, r"scheduler\.add_job\(", exclude=("main.py",))
    if serverless and (scheduler_on or extra_jobs):
        findings.append(Finding(
            "error", "APScheduler needs a long-running process, which Vercel functions don't have.",
            "Set ENABLE_SCHEDULER=false and move periodic work to Vercel Cron Jobs that call an endpoint.",
            _locations(extra_jobs) if extra_jobs else None,
        ))
    elif not serverless and (scheduler_on or extra_jobs):
        findings.append(Finding(
            "warning", "Cloud Run throttles CPU between requests and scales to zero, so APScheduler jobs run late "
            "or not at all.",
            "Set ENABLE_SCHEDULER=false and use Cloud Scheduler to call an endpoint (cheapest), or deploy with "
            "--no-cpu-throttling --min-instances 1 (billed around the clock).",
            _locations(extra_jobs) if extra_jobs else None,
        ))

    queue_calls = _scan(project, r"\.enqueue\(|\.delay\(|\.apply_async\(", exclude=("core/email/manager.py", "core/queue/manager.py"))
    if _is_true(env.get("EMAIL_QUEUE_ENABLED"), True):
        findings.append(Finding(
            "error" if serverless else "warning",
            "EMAIL_QUEUE_ENABLED=true hands emails to a Celery worker. Without a running worker, emails are "
            "queued and never sent.",
            "Set EMAIL_QUEUE_ENABLED=false to send emails during the request"
            + (" (Vercel can't run workers)." if serverless else
               ", or run the worker as a second Cloud Run service with --no-cpu-throttling --min-instances 1."),
        ))
    if queue_calls:
        findings.append(Finding(
            "error" if serverless else "warning",
            "Code enqueues Celery tasks, which only run if a worker process is deployed.",
            "Await the task function directly, or deploy a worker"
            + (" elsewhere; Vercel can't run one." if serverless else " as a separate Cloud Run service."),
            _locations(queue_calls),
        ))

    websockets = _scan(project, r"\.websocket\(|\bWebSocket\b")
    if websockets and serverless:
        findings.append(Finding(
            "error", "WebSocket endpoints don't work on Vercel functions.",
            "Deploy to Cloud Run instead, or use a hosted realtime service (Pusher, Ably, Supabase Realtime).",
            _locations(websockets),
        ))

    background = _scan(project, r"\bBackgroundTasks\b")
    if background:
        findings.append(Finding(
            "warning",
            "BackgroundTasks run after the response is sent. "
            + ("Vercel may freeze the function at that point, so they can be cut off."
               if serverless else "Cloud Run throttles CPU after the response, so they run slowly or stall."),
            "Await the work before responding"
            + ("." if serverless else ", or deploy with --no-cpu-throttling."),
            _locations(background),
        ))
    return findings


def _check_platform_files(project: Path, target: str) -> list[Finding]:
    findings = []
    if target == "vercel":
        if not (project / "vercel.json").exists():
            findings.append(Finding(
                "error", "vercel.json is missing. Without it Vercel treats every file in api/ as its own function "
                "and the build fails.",
                "Run: fasterapi deploy init vercel",
            ))
        requirements = (project / "requirements.txt")
        if requirements.exists() and re.search(r"^\s*flower\b", requirements.read_text(encoding="utf-8"), re.M | re.I):
            findings.append(Finding(
                "warning", "requirements.txt includes flower, a Celery dashboard that is unused on Vercel and "
                "adds to bundle size and cold starts.",
                "Remove flower (and celery if you don't use a worker) from requirements.txt.",
            ))
    else:
        dockerfile = project / "Dockerfile"
        if not dockerfile.exists():
            findings.append(Finding("error", "Dockerfile is missing.", "Run: fasterapi deploy init cloudrun"))
        elif "PORT" not in dockerfile.read_text(encoding="utf-8"):
            findings.append(Finding(
                "error", "The Dockerfile doesn't listen on $PORT, so Cloud Run's startup check fails.",
                "Run: fasterapi deploy init cloudrun (it backs up the current Dockerfile).",
            ))
        dockerignore = project / ".dockerignore"
        if not dockerignore.exists() or not re.search(r"^\.env\s*$", dockerignore.read_text(encoding="utf-8"), re.M):
            findings.append(Finding(
                "error", ".dockerignore doesn't exclude .env, so your secrets would be baked into the image.",
                "Run: fasterapi deploy init cloudrun",
            ))
    return findings


def check_project(target: str, project: Path | None = None, env_file: str | None = None) -> tuple[list[Finding], str | None]:
    project = project or Path.cwd()
    env, env_name = load_env(project, env_file)
    findings = (
        _check_platform_files(project, target)
        + _check_services(env, target)
        + _check_runtime_features(project, env, target)
    )
    findings.sort(key=lambda finding: finding.severity != "error")
    return findings, env_name


def print_findings(findings: list[Finding], target: str, env_name: str | None) -> bool:
    label = "Vercel" if target == "vercel" else "Google Cloud Run"
    print(f"🔎 Checking project for {label} (settings from {env_name or 'no .env file'})")
    if not findings:
        print("✅ No problems found.")
        return True
    for finding in findings:
        icon = "❌" if finding.severity == "error" else "⚠️ "
        print(f"\n{icon} {finding.message}")
        if finding.location:
            print(f"   at {finding.location}")
        print(f"   fix: {finding.fix}")
    errors = sum(finding.severity == "error" for finding in findings)
    warnings = len(findings) - errors
    print(f"\n{errors} error(s), {warnings} warning(s).")
    return errors == 0


def _write(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"kept existing {path.name}"
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    path.write_text(content, encoding="utf-8")
    return f"wrote {path.name}"


def apply_env_preset(target: str, project: Path) -> None:
    from fasterapi.scaffolder.database_setup import _set_env_value

    for env_path in (project / ".env.example", project / ".env"):
        if env_path.exists():
            for key, value in _ENV_PRESETS[target].items():
                _set_env_value(env_path, key, value)


def init_target(target: str, project: Path | None = None, force: bool = False) -> bool:
    project = project or Path.cwd()
    if not (project / "main.py").exists():
        print("❌ main.py not found. Run this from your project root.")
        return False

    actions = []
    if target == "vercel":
        actions.append(_write(project / "vercel.json", json.dumps(_VERCEL_JSON, indent=2) + "\n", force))
        actions.append(_write(project / ".vercelignore", _VERCEL_IGNORE, force))
    else:
        dockerfile = project / "Dockerfile"
        needs_dockerfile = force or not dockerfile.exists() or "PORT" not in dockerfile.read_text(encoding="utf-8")
        actions.append(_write(dockerfile, (TEMPLATE_ROOT / "Dockerfile").read_text(encoding="utf-8"), needs_dockerfile))
        dockerignore = project / ".dockerignore"
        if dockerignore.exists() and not re.search(r"^\.env\s*$", dockerignore.read_text(encoding="utf-8"), re.M):
            dockerignore.write_text(dockerignore.read_text(encoding="utf-8").rstrip("\n") + "\n.env\n", encoding="utf-8")
            actions.append("added .env to .dockerignore")
        else:
            actions.append(_write(dockerignore, (TEMPLATE_ROOT / ".dockerignore").read_text(encoding="utf-8"), force))
        actions.append(_write(project / ".gcloudignore", _GCLOUD_IGNORE, force))

    apply_env_preset(target, project)
    actions.append("set ENABLE_SCHEDULER=false and EMAIL_QUEUE_ENABLED=false in your env files")
    for action in actions:
        print(f"🔧 {action}")
    print(f"✅ Project prepared for {'Vercel' if target == 'vercel' else 'Google Cloud Run'}.")
    print(f"💡 Next: fasterapi deploy check --target {target}")
    return True


def _deploy_env(env: dict[str, str], target: str) -> dict[str, str]:
    values = {key: value for key, value in env.items() if value}
    if target == "cloudrun":
        values = {key: value for key, value in values.items() if key not in _CLOUDRUN_RESERVED}
        # One worker per vCPU keeps memory within the default 512Mi.
        values.setdefault("WEB_CONCURRENCY", "1")
    return values


def _run(command: list[str], dry_run: bool, **kwargs) -> bool:
    print("$ " + " ".join(command))
    if dry_run:
        return True
    try:
        subprocess.run(command, check=True, **kwargs)
        return True
    except FileNotFoundError:
        print(f"❌ {command[0]} is not installed or not on PATH.")
    except subprocess.CalledProcessError as exc:
        print(f"❌ {command[0]} exited with status {exc.returncode}.")
    return False


def deploy_cloudrun(
    service: str,
    region: str,
    gcp_project: str | None,
    env_file: str | None,
    allow_unauthenticated: bool,
    min_instances: int,
    max_instances: int,
    memory: str,
    cpu: str,
    dry_run: bool,
    force: bool,
) -> bool:
    project = Path.cwd()
    findings, env_name = check_project("cloudrun", project, env_file)
    if not print_findings(findings, "cloudrun", env_name) and not force:
        print("🛑 Fix the errors above, or pass --force to deploy anyway.")
        return False
    if not dry_run and shutil.which("gcloud") is None:
        print("❌ gcloud CLI not found. Install it from https://cloud.google.com/sdk/docs/install and run: gcloud auth login")
        return False

    env, _ = load_env(project, env_file)
    variables = _deploy_env(env, "cloudrun")
    handle, env_path = tempfile.mkstemp(prefix="fasterapi-cloudrun-", suffix=".yaml")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            # JSON strings are valid YAML scalars, so no YAML dependency is needed.
            file.write("".join(f"{key}: {json.dumps(value)}\n" for key, value in variables.items()))
        command = [
            "gcloud", "run", "deploy", service, "--source", ".", "--region", region,
            "--env-vars-file", env_path,
            "--min-instances", str(min_instances), "--max-instances", str(max_instances),
            "--memory", memory, "--cpu", cpu,
            "--allow-unauthenticated" if allow_unauthenticated else "--no-allow-unauthenticated",
        ]
        if gcp_project:
            command += ["--project", gcp_project]
        print(f"🚀 Deploying with {len(variables)} environment variable(s) from {env_name or 'no env file'}.")
        print("   Tip: move secrets to Secret Manager and use --set-secrets for stricter access control.")
        return _run(command, dry_run)
    finally:
        os.unlink(env_path)


def deploy_vercel(prod: bool, push_env: bool, env_file: str | None, dry_run: bool, force: bool) -> bool:
    project = Path.cwd()
    findings, env_name = check_project("vercel", project, env_file)
    if not print_findings(findings, "vercel", env_name) and not force:
        print("🛑 Fix the errors above, or pass --force to deploy anyway.")
        return False
    if not dry_run and shutil.which("vercel") is None:
        print("❌ Vercel CLI not found. Install it with: npm i -g vercel, then run: vercel login")
        return False

    if push_env:
        env, _ = load_env(project, env_file)
        environment = "production" if prod else "preview"
        for key, value in _deploy_env(env, "vercel").items():
            print(f"$ vercel env add {key} {environment}")
            if dry_run:
                continue
            result = subprocess.run(["vercel", "env", "add", key, environment], input=value, text=True, capture_output=True)
            if result.returncode != 0:
                detail = (result.stderr.strip().splitlines() or ["no details"])[-1]
                print(f"   skipped {key}: already set or rejected ({detail})")

    return _run(["vercel", "deploy"] + (["--prod"] if prod else []), dry_run)
