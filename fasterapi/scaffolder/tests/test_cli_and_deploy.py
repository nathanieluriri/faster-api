from __future__ import annotations

import json
import shutil
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from fasterapi.cli import cli
from fasterapi.scaffolder.deploy import check_project

READY_ENV = {
    "DB_TYPE": "postgres",
    "DATABASE_URL": "postgresql://u:p@db.example.com:5432/app",
    "REDIS_URL": "rediss://default:p@cache.example.com:6379",
    "SECRET_KEY": "s" * 40,
    "SESSION_SECRET_KEY": "t" * 40,
    "ENV": "production",
    "STORAGE_BACKEND": "s3",
    "ENABLE_SCHEDULER": "false",
    "EMAIL_QUEUE_ENABLED": "false",
}


@pytest.fixture()
def runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return CliRunner()


def _new_project(runner, *args) -> Path:
    result = runner.invoke(cli, ["new", "app", *args])
    assert result.exit_code == 0, result.output
    return Path.cwd() / "app"


def _write_env(project: Path, **overrides) -> None:
    values = {**READY_ENV, **overrides}
    (project / ".env").write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")


def _messages(project: Path, target: str) -> list[tuple[str, str]]:
    findings, _ = check_project(target, project)
    return [(f.severity, f.message) for f in findings]


def test_new_with_postgres_and_vercel_prepares_project(runner):
    project = _new_project(runner, "--db", "supabase", "--deploy", "vercel")
    env = (project / ".env.example").read_text()
    assert "DB_TYPE=supabase" in env and "ENABLE_SCHEDULER=false" in env and "EMAIL_QUEUE_ENABLED=false" in env
    assert "asyncpg" in (project / "requirements.txt").read_text().split()
    assert json.loads((project / "vercel.json").read_text())["builds"][0]["src"] == "main.py"


def test_ready_project_passes_both_checks(runner):
    project = _new_project(runner, "--deploy", "cloudrun")
    (project / "vercel.json").write_text("{}")
    _write_env(project)
    for target in ("vercel", "cloudrun"):
        assert [s for s, _ in _messages(project, target) if s == "error"] == []


def test_vercel_check_flags_serverless_incompatible_features(runner):
    project = _new_project(runner, "--deploy", "vercel")
    _write_env(project, STORAGE_BACKEND="local", ENABLE_SCHEDULER="true", EMAIL_QUEUE_ENABLED="true", REDIS_URL="redis://localhost:6379")
    (project / "api" / "v1" / "live_route.py").write_text("from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.websocket('/ws')\nasync def ws(socket):\n    pass\n")
    errors = " ".join(m for s, m in _messages(project, "vercel") if s == "error")
    for expected in ("STORAGE_BACKEND=local", "APScheduler", "EMAIL_QUEUE_ENABLED", "WebSocket", "Redis"):
        assert expected in errors


def test_cloudrun_treats_worker_features_as_warnings(runner):
    project = _new_project(runner, "--deploy", "cloudrun")
    _write_env(project, ENABLE_SCHEDULER="true", EMAIL_QUEUE_ENABLED="true")
    findings = _messages(project, "cloudrun")
    assert [s for s, _ in findings if s == "error"] == []
    assert any("APScheduler" in m for _, m in findings)


def test_cloudrun_check_catches_old_dockerfile_and_env_in_image(runner):
    project = _new_project(runner)
    _write_env(project)
    (project / "Dockerfile").write_text('FROM python:3.11-slim\nCMD ["gunicorn", "--bind", "0.0.0.0:7860", "main:app"]\n')
    (project / ".dockerignore").unlink()
    errors = [m for s, m in _messages(project, "cloudrun") if s == "error"]
    assert any("$PORT" in m for m in errors) and any(".env" in m for m in errors)

    assert runner.invoke(cli, ["deploy", "init", "cloudrun"], catch_exceptions=False).exit_code != 0  # not in project root
    os.chdir(project)
    assert runner.invoke(cli, ["deploy", "init", "cloudrun"]).exit_code == 0
    assert (project / "Dockerfile.bak").exists()
    assert [m for s, m in _messages(project, "cloudrun") if s == "error"] == []


def test_deploy_check_exit_code_and_supabase_pooler_hint(runner):
    project = _new_project(runner, "--db", "supabase", "--deploy", "vercel")
    _write_env(project, DB_TYPE="supabase", DATABASE_URL="postgresql://u:p@db.abc.supabase.co:5432/postgres")
    os.chdir(project)
    result = runner.invoke(cli, ["deploy", "check", "--target", "vercel"])
    assert result.exit_code == 0, result.output
    assert "transaction pooler" in result.output
    _write_env(project, SECRET_KEY="")
    assert runner.invoke(cli, ["deploy", "check", "--target", "vercel"]).exit_code == 1


def test_cloudrun_dry_run_skips_reserved_and_empty_env(runner):
    project = _new_project(runner, "--deploy", "cloudrun")
    _write_env(project, PORT="8080", EMPTY_VALUE="")
    os.chdir(project)
    result = runner.invoke(cli, ["deploy", "cloudrun", "--service", "api", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "gcloud run deploy api --source . --region us-central1" in result.output
    assert "--max-instances 3" in result.output and "--min-instances 0" in result.output

    from fasterapi.scaffolder.deploy import _deploy_env, load_env
    variables = _deploy_env(load_env(project)[0], "cloudrun")
    assert "PORT" not in variables and "EMPTY_VALUE" not in variables and variables["WEB_CONCURRENCY"] == "1"


def test_db_use_upgrades_old_project_files(runner):
    project = _new_project(runner)
    (project / "core" / "database.py").write_text("DB_TYPE = 'sqlite'\n")
    (project / "core" / "postgres_store.py").unlink()
    os.chdir(project)
    result = runner.invoke(cli, ["db", "use", "postgres"])
    assert result.exit_code == 0, result.output
    assert "ping_database" in (project / "core" / "database.py").read_text()
    assert (project / "core" / "database.py.bak").read_text() == "DB_TYPE = 'sqlite'\n"
    assert (project / "core" / "postgres_store.py").exists()
    assert "DB_TYPE=postgres" in (project / ".env.example").read_text()
    runner.invoke(cli, ["db", "use", "postgres"])
    assert (project / "requirements.txt").read_text().split().count("asyncpg") == 1


def test_generators_guard_existing_files_and_reject_filter_operators(runner):
    project = _new_project(runner)
    os.chdir(project)
    for command in (["make-schema", "item"], ["make-crud", "item"], ["make-service", "item"], ["make-route", "item", "-y"]):
        assert runner.invoke(cli, command).exit_code == 0
    (project / "repositories" / "item.py").write_text("# custom edits\n")
    assert runner.invoke(cli, ["make-crud", "item"]).exit_code != 0
    assert (project / "repositories" / "item.py").read_text() == "# custom edits\n"
    assert runner.invoke(cli, ["make-schema", "item"]).exit_code != 0

    route = (project / "api" / "v1" / "item.py").read_text()
    assert 'str(key).startswith("$")' in route
    assert "payload: ItemUpdate," in route and "ItemUpdate = None" not in route
    assert "{db_name}" not in route


def test_mount_and_make_route_fail_cleanly_outside_a_project(runner):
    result = runner.invoke(cli, ["mount"])
    assert result.exit_code != 0 and "Failed to mount routes" in result.output
    result = runner.invoke(cli, ["make-route", "thing", "-y"])
    assert result.exit_code != 0 and "Traceback" not in result.output


def test_generated_schema_imports(runner):
    project = _new_project(runner)
    os.chdir(project)
    runner.invoke(cli, ["make-schema", "widget"])
    import subprocess, sys
    completed = subprocess.run([sys.executable, "-c", "import schemas.widget"], cwd=project, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_bootstrapped_project_tests_pass(runner):
    import subprocess, sys
    project = _new_project(runner)
    (project / ".env").write_text((project / ".env.example").read_text())
    completed = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=project, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout[-2000:]


def test_split_user_produces_an_importable_app(runner):
    import subprocess, sys
    project = _new_project(runner)
    (project / ".env").write_text((project / ".env.example").read_text())
    os.chdir(project)
    result = runner.invoke(cli, ["split-user"], input="driver\nrider\nend\n")
    assert result.exit_code == 0, result.output
    completed = subprocess.run([sys.executable, "-c", "import main"], cwd=project, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr[-1500:]


def test_vercelignore_keeps_every_module_main_imports(runner):
    project = _new_project(runner, "--deploy", "vercel")
    ignored = {line.strip() for line in (project / ".vercelignore").read_text().splitlines()}
    imported = {line.split()[1].split(".")[0] for line in (project / "main.py").read_text().splitlines() if line.startswith(("from ", "import "))}
    assert not {f"{name}.py" for name in imported} & ignored
    assert not imported & ignored


def test_deploy_check_rejects_a_weak_super_admin_password(runner):
    project = _new_project(runner, "--deploy", "cloudrun")
    _write_env(project, SUPER_ADMIN_EMAIL="root@example.com", SUPER_ADMIN_PASSWORD="string")
    assert any("SUPER_ADMIN_PASSWORD" in m for s, m in _messages(project, "cloudrun") if s == "error")
    _write_env(project, SUPER_ADMIN_EMAIL="root@example.com", SUPER_ADMIN_PASSWORD="a-long-random-password")
    assert [m for s, m in _messages(project, "cloudrun") if s == "error"] == []


def test_make_account_wires_the_role_and_survives_split_and_unsplit(runner):
    import subprocess, sys
    project = _new_project(runner)
    (project / ".env").write_text((project / ".env.example").read_text())
    os.chdir(project)

    def importable():
        return subprocess.run([sys.executable, "-c", "import main"], cwd=project, capture_output=True, text=True)

    assert runner.invoke(cli, ["make-account", "customer"]).exit_code == 0
    for relative in ("security/auth.py", "security/account_status_check.py", "repositories/tokens_repo.py"):
        assert "customer" in (project / relative).read_text()
    assert "retrieve_customer_by_customer_id" in (project / "services" / "customer_service.py").read_text()
    assert json.loads((project / ".fasterapi" / "role_split_state.json").read_text())["extra_roles"] == ["customer"]
    assert importable().returncode == 0, importable().stderr[-1500:]

    assert runner.invoke(cli, ["split-user"], input="driver\nrider\nend\n").exit_code == 0
    assert (project / "api" / "v1" / "customer_route.py").exists()
    assert "verify_customer_token" in (project / "security" / "auth.py").read_text()
    assert importable().returncode == 0, importable().stderr[-1500:]

    assert runner.invoke(cli, ["unsplit-user"], input="yes\n").exit_code == 0
    assert (project / "api" / "v1" / "customer_route.py").exists() and (project / "api" / "v1" / "user_route.py").exists()
    assert "verify_customer_token" in (project / "security" / "auth.py").read_text()
    assert importable().returncode == 0, importable().stderr[-1500:]


def test_make_account_rejects_reserved_duplicate_and_clashing_names(runner):
    project = _new_project(runner)
    os.chdir(project)
    assert runner.invoke(cli, ["make-account", "customer"]).exit_code == 0
    for name in ("user", "admin", "customer", "payment", "Bad-Name"):
        assert runner.invoke(cli, ["make-account", name]).exit_code != 0, name


def test_deploy_check_warns_when_proxy_hops_are_disabled(runner):
    project = _new_project(runner, "--deploy", "vercel")
    _write_env(project, TRUSTED_PROXY_HOPS="0")
    assert any("TRUSTED_PROXY_HOPS" in m for s, m in _messages(project, "vercel") if s == "warning")


def test_deploy_check_requires_webhook_secrets_for_configured_payments(runner):
    project = _new_project(runner, "--deploy", "cloudrun")
    _write_env(project, STRIPE_SECRET_KEY="sk_live_x", STRIPE_WEBHOOK_SECRET="")
    assert any("STRIPE_WEBHOOK_SECRET" in m for s, m in _messages(project, "cloudrun") if s == "error")
    _write_env(project, STRIPE_SECRET_KEY="sk_live_x", STRIPE_WEBHOOK_SECRET="whsec_x")
    assert [m for s, m in _messages(project, "cloudrun") if s == "error"] == []


def test_email_mount_rejects_broken_templates_and_rolls_back(runner):
    project = _new_project(runner)
    os.chdir(project)
    mounted = project / "core" / "email" / "mounted_templates.py"
    before = mounted.read_text()

    (project / "custom_templates" / "return.py").write_text((project / "email_templates" / "starter_template.py").read_text())
    assert runner.invoke(cli, ["email", "mount-custom"]).exit_code != 0
    assert (project / "custom_templates" / "return.py").exists()
    (project / "custom_templates" / "return.py").unlink()

    (project / "email_templates" / "bad.py").write_text(
        'raise RuntimeError("boom")\nTEMPLATE_KEY = "bad"\nSUBJECT = "Bad"\n'
        "def render_html(context):\n    return ''\ndef render_text(context):\n    return ''\n"
    )
    assert runner.invoke(cli, ["email", "mount"]).exit_code != 0
    assert mounted.read_text() == before
    (project / "email_templates" / "bad.py").unlink()

    result = runner.invoke(cli, ["email", "add-template", "--template-key", "otp"])
    assert result.exit_code == 0 and 'template_key="otp"' in result.output
    assert runner.invoke(cli, ["email", "mount"]).exit_code == 0
    assert "email_templates.otp_template" in mounted.read_text()


def test_email_commands_refuse_to_run_outside_a_project(runner):
    assert runner.invoke(cli, ["email", "mount"]).exit_code != 0
    assert not (Path.cwd() / "email_templates").exists()


def test_make_token_repo_protects_edits_validates_roles_and_keeps_project_roles(runner):
    project = _new_project(runner)
    os.chdir(project)
    tokens = project / "repositories" / "tokens_repo.py"
    tokens.write_text(tokens.read_text() + "# my edit\n")
    assert runner.invoke(cli, ["make-token-repo", "admin", "user"]).exit_code != 0
    assert runner.invoke(cli, ["make-token-repo", "admin", "support.agent", "--force"]).exit_code != 0
    assert "# my edit" in tokens.read_text()

    assert runner.invoke(cli, ["make-account", "customer"]).exit_code == 0
    result = runner.invoke(cli, ["make-token-repo", "--force"])
    assert result.exit_code == 0 and "admin, user, customer" in result.output
    assert "def add_customer_access_token" in tokens.read_text()
    assert (project / "repositories" / "tokens_repo.py.bak").exists()


def test_project_python_prefers_the_project_environment(tmp_path, monkeypatch):
    import sys
    from fasterapi.scaffolder.project_python import project_python

    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert project_python(tmp_path) == sys.executable
    local = tmp_path / ".venv" / "bin" / "python"
    local.parent.mkdir(parents=True)
    local.write_text("")
    assert project_python(tmp_path) == str(local)
    active = tmp_path / "active" / "bin" / "python"
    active.parent.mkdir(parents=True)
    active.write_text("")
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "active"))
    assert project_python(tmp_path) == str(active)


def test_new_projects_never_include_bytecode_caches(runner, tmp_path):
    cache = Path(__file__).resolve().parents[1] / "templates" / "project_template" / "core" / "__pycache__"
    cache.mkdir(exist_ok=True)
    try:
        project = _new_project(runner)
        assert not list(project.rglob("__pycache__"))
    finally:
        shutil.rmtree(cache, ignore_errors=True)
