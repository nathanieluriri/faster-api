from __future__ import annotations

import re
import shutil
from pathlib import Path

BACKENDS = ("mongodb", "postgres", "supabase")
TEMPLATE_ROOT = Path(__file__).parent / "templates" / "project_template"

# Files that older projects may have in a MongoDB-only form.
_CORE_FILES = {
    "core/database.py": "ping_database",
    "core/scheduler.py": "DB_TYPE",
    "core/postgres_store.py": "PostgresDocumentStore",
}


def _set_env_value(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _has_env_key(path: Path, key: str) -> bool:
    return path.exists() and re.search(rf"^\s*{re.escape(key)}\s*=", path.read_text(encoding="utf-8"), re.M) is not None


def _ensure_requirement(project: Path, package: str) -> bool:
    requirements = project / "requirements.txt"
    lines = requirements.read_text(encoding="utf-8").splitlines() if requirements.exists() else []
    names = {re.split(r"[\[<>=!~ ]", line.strip(), maxsplit=1)[0].lower() for line in lines if line.strip()}
    if package.lower() in names:
        return False
    lines.append(package)
    requirements.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _sync_core_files(project: Path) -> list[str]:
    updated = []
    for relative, marker in _CORE_FILES.items():
        target = project / relative
        if target.exists() and marker in target.read_text(encoding="utf-8"):
            continue
        if target.exists():
            shutil.copy2(target, target.with_name(target.name + ".bak"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE_ROOT / relative, target)
        updated.append(relative)
    return updated


def use_database(backend: str, project: Path | None = None) -> bool:
    backend = backend.lower()
    project = project or Path.cwd()
    if backend not in BACKENDS:
        print(f"❌ Unsupported database '{backend}'. Choose one of: {', '.join(BACKENDS)}")
        return False
    if not (project / "main.py").exists() or not (project / "core").is_dir():
        print("❌ This doesn't look like a FasterAPI project (main.py and core/ are required).")
        return False

    for relative in _sync_core_files(project):
        print(f"🔧 Updated {relative} (previous version saved as {relative}.bak if it existed)")

    for env_file in (project / ".env.example", project / ".env"):
        if not env_file.exists():
            continue
        _set_env_value(env_file, "DB_TYPE", backend)
        if backend != "mongodb" and not _has_env_key(env_file, "DATABASE_URL"):
            _set_env_value(env_file, "DATABASE_URL", "")

    if backend != "mongodb" and _ensure_requirement(project, "asyncpg"):
        print("📦 Added asyncpg to requirements.txt (run: pip install -r requirements.txt)")

    print(f"✅ Database set to {backend}.")
    if backend == "supabase":
        print("💡 Set DATABASE_URL to your Supabase connection string (Project Settings > Database).")
        print("   Use the transaction pooler URL (port 6543) for Vercel or other serverless hosts.")
    elif backend == "postgres":
        print("💡 Set DATABASE_URL, e.g. postgresql://user:password@host:5432/dbname (Neon and Cloud SQL work too).")
    if backend != "mongodb":
        print("   Tables are created automatically on first use. MongoDB-only query operators raise a clear error.")
    return True
