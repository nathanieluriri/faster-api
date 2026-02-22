from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import click

from fasterapi.scaffolder.generate_account import _apply_replacements
from fasterapi.scaffolder.generate_tokens_repo import create_token_file
from fasterapi.scaffolder.mount_routes import update_main_routes


ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
RESERVED_ROLE_NAMES = {"admin", "anonymous", "member", "user"}
SPLIT_STATE_FILE = Path(".fasterapi") / "role_split_state.json"
DEFAULT_ANONYMOUS_RATE = "20/minute"
DEFAULT_ROLE_RATE = "80/minute"
DEFAULT_ADMIN_RATE = "140/minute"


@dataclass(frozen=True)
class ProjectLayout:
    root: Path
    schemas_dir: Path
    repositories_dir: Path
    services_dir: Path
    routes_dir: Path
    security_dir: Path


@dataclass(frozen=True)
class RoleSplitState:
    version: int
    mode: str
    roles: tuple[str, ...]
    previous_primary_role: str
    created_at: str
    touched_files: tuple[str, ...]
    archived_at: str | None = None
    last_unsplit_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "mode": self.mode,
            "roles": list(self.roles),
            "previous_primary_role": self.previous_primary_role,
            "created_at": self.created_at,
            "touched_files": list(self.touched_files),
            "archived_at": self.archived_at,
            "last_unsplit_at": self.last_unsplit_at,
        }


def run_split_user_wizard(force: bool = False) -> bool:
    """Run the interactive split-user flow and apply conversion."""
    first_role = _prompt_role_name(prompt="Split user to what?", existing=())
    roles: list[str] = [first_role]

    click.echo("1. Enter name of the next role")
    second_role = _prompt_role_name(prompt="Enter role name", existing=roles)
    roles.append(second_role)

    while True:
        click.echo("1. Enter name of next role")
        click.echo(f"2. Type end to convert to split into {_humanize_roles(roles)}")

        action = click.prompt("Select option", type=str).strip().lower()
        if action in {"2", "end"}:
            break
        if action == "1":
            next_role = _prompt_role_name(prompt="Enter role name", existing=roles)
            roles.append(next_role)
            continue

        click.echo("❌ Invalid choice. Enter 1 or type end.")

    return perform_split(roles=roles, force=force)


def run_unsplit_user_wizard(force: bool = False) -> bool:
    """Run the interactive unsplit-user flow and apply conversion."""
    project_root = Path.cwd()
    state = _read_state(project_root)
    roles = list(state.roles) if state and state.mode == "split" else _detect_split_roles(project_root)

    if not roles:
        click.echo("ℹ️ No split roles detected. Project is already in unsplit mode.")
        return False

    click.echo(f"Detected split roles: {', '.join(roles)}")
    confirmation = click.prompt("Type 'yes' to collapse roles back to user", type=str).strip().lower()
    if confirmation != "yes":
        click.echo("Aborted. No changes were made.")
        return False

    return perform_unsplit(force=force)


def perform_split(roles: list[str], force: bool = False) -> bool:
    """Convert a project from unsplit user mode to custom split-role mode."""
    validated_roles = _validate_roles(roles)
    layout = _resolve_layout(Path.cwd())

    existing_state = _read_state(layout.root)
    if existing_state and existing_state.mode == "split" and list(existing_state.roles) == validated_roles:
        click.echo(f"ℹ️ Project already split into {_humanize_roles(validated_roles)}. No changes required.")
        return True

    files_to_touch = _collect_split_touch_files(validated_roles)
    if not force:
        conflict_files = _find_conflict_marker_files(layout.root, files_to_touch)
        if conflict_files:
            click.echo("❌ Aborting: unresolved merge conflict markers found in files below:")
            for path in conflict_files:
                click.echo(f"   - {path}")
            click.echo("Run with --force to override this safety check.")
            return False

    timestamp = _timestamp_slug()
    archive_root = layout.root / ".fasterapi" / "archive" / timestamp
    archived_files = _archive_existing_files(layout.root, files_to_touch, archive_root)

    # Create role-specific modules by cloning current user files from the active project.
    user_sources = {
        Path("schemas/user_schema.py"): layout.schemas_dir,
        Path("repositories/user_repo.py"): layout.repositories_dir,
        Path("services/user_service.py"): layout.services_dir,
        Path("api/v1/user_route.py"): layout.routes_dir,
    }
    _ensure_required_sources(layout.root, user_sources.keys())

    generated_files: list[str] = []
    for role in validated_roles:
        for source_relative, destination_dir in user_sources.items():
            source_path = layout.root / source_relative
            source_content = source_path.read_text(encoding="utf-8")
            rewritten = _apply_replacements(source_content, role)
            rewritten = _rewrite_role_specific_content(rewritten, role)
            destination_file = destination_dir / source_relative.name.replace("user_", f"{role}_")
            destination_file.write_text(rewritten, encoding="utf-8")
            generated_files.append(str(destination_file.relative_to(layout.root)).replace("\\", "/"))

    # Remove legacy user files from active split mode.
    legacy_user_files = [
        Path("schemas/user_schema.py"),
        Path("repositories/user_repo.py"),
        Path("services/user_service.py"),
        Path("api/v1/user_route.py"),
    ]
    for relative_path in legacy_user_files:
        file_path = layout.root / relative_path
        if file_path.exists():
            file_path.unlink()

    _write_role_runtime_files(layout.root, non_admin_roles=validated_roles)
    create_token_file(["admin", *validated_roles])
    update_main_routes()

    rate_limits_csv = _build_role_rate_limits_csv(validated_roles)
    _upsert_env_var(layout.root / ".env.example", "ROLE_RATE_LIMITS", rate_limits_csv)

    touched_files = sorted(set(files_to_touch + generated_files + archived_files))
    state = RoleSplitState(
        version=1,
        mode="split",
        roles=tuple(validated_roles),
        previous_primary_role="user",
        created_at=_iso_now(),
        touched_files=tuple(touched_files),
        archived_at=timestamp,
    )
    _write_state(layout.root, state)

    _write_report(
        layout.root / "split_user_report.md",
        title="Split User Report",
        body_lines=[
            f"Converted to split roles: {', '.join(validated_roles)}",
            f"Archive folder: .fasterapi/archive/{timestamp}",
            "Updated runtime auth/principal/account checks for role-aware verification.",
            f"Applied ROLE_RATE_LIMITS default: `{rate_limits_csv}`",
            f"Generated files: {', '.join(generated_files)}",
        ],
    )

    click.echo(f"✅ Split conversion completed for roles: {', '.join(validated_roles)}")
    return True


def perform_unsplit(force: bool = False) -> bool:
    """Convert a project from split-role mode back to canonical user/admin mode."""
    layout = _resolve_layout(Path.cwd())
    state = _read_state(layout.root)
    split_roles = list(state.roles) if state and state.mode == "split" else _detect_split_roles(layout.root)

    if not split_roles:
        click.echo("ℹ️ No split roles detected. Nothing to unsplit.")
        return False

    files_to_touch = _collect_unsplit_touch_files(split_roles)
    if not force:
        conflict_files = _find_conflict_marker_files(layout.root, files_to_touch)
        if conflict_files:
            click.echo("❌ Aborting: unresolved merge conflict markers found in files below:")
            for path in conflict_files:
                click.echo(f"   - {path}")
            click.echo("Run with --force to override this safety check.")
            return False

    timestamp = _timestamp_slug()
    archive_root = layout.root / ".fasterapi" / "archive" / timestamp
    archived_files = _archive_existing_files(layout.root, files_to_touch, archive_root)

    # Archive split-specific role files before removal.
    split_archive_root = archive_root / "split_roles"
    for role in split_roles:
        role_paths = [
            layout.root / "schemas" / f"{role}_schema.py",
            layout.root / "repositories" / f"{role}_repo.py",
            layout.root / "services" / f"{role}_service.py",
            layout.root / "api" / "v1" / f"{role}_route.py",
        ]
        for path in role_paths:
            if not path.exists():
                continue
            target = split_archive_root / path.relative_to(layout.root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            path.unlink()

    # Restore canonical user files from package templates.
    template_root = Path(__file__).parent / "templates" / "project_template"
    canonical_files = [
        Path("schemas/user_schema.py"),
        Path("repositories/user_repo.py"),
        Path("services/user_service.py"),
        Path("api/v1/user_route.py"),
    ]
    for relative_path in canonical_files:
        source = template_root / relative_path
        if not source.exists():
            raise click.ClickException(f"Missing template file required for unsplit: {source}")
        destination = layout.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    _write_role_runtime_files(layout.root, non_admin_roles=["user"])
    create_token_file(["admin", "user"])
    update_main_routes()

    rate_limits_csv = _build_role_rate_limits_csv(["user"])
    _upsert_env_var(layout.root / ".env.example", "ROLE_RATE_LIMITS", rate_limits_csv)

    new_state = RoleSplitState(
        version=1,
        mode="unsplit",
        roles=tuple(),
        previous_primary_role="user",
        created_at=state.created_at if state else _iso_now(),
        touched_files=tuple(sorted(set(files_to_touch + archived_files))),
        archived_at=timestamp,
        last_unsplit_at=_iso_now(),
    )
    _write_state(layout.root, new_state)

    _write_report(
        layout.root / "unsplit_user_report.md",
        title="Unsplit User Report",
        body_lines=[
            "Collapsed split roles back into canonical `user` role.",
            f"Archived split-role files under: .fasterapi/archive/{timestamp}/split_roles",
            f"Reset ROLE_RATE_LIMITS default to `{rate_limits_csv}`",
            "Rebuilt auth/principal/account checks for user/admin mode.",
        ],
    )

    click.echo("✅ Unsplit conversion completed. Project is now in user/admin mode.")
    return True


def _resolve_layout(root: Path) -> ProjectLayout:
    layout = ProjectLayout(
        root=root,
        schemas_dir=root / "schemas",
        repositories_dir=root / "repositories",
        services_dir=root / "services",
        routes_dir=root / "api" / "v1",
        security_dir=root / "security",
    )
    required = [
        layout.schemas_dir,
        layout.repositories_dir,
        layout.services_dir,
        layout.routes_dir,
        layout.security_dir,
        root / "main.py",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise click.ClickException(
            "This command must run from a FasterAPI project root. Missing: " + ", ".join(missing)
        )
    return layout


def _prompt_role_name(prompt: str, existing: Iterable[str]) -> str:
    while True:
        candidate = click.prompt(prompt, type=str).strip().lower()
        error = _validate_role_name(candidate, existing=existing)
        if error is None:
            return candidate
        click.echo(f"❌ {error}")


def _validate_roles(roles: list[str]) -> list[str]:
    normalized = [role.strip().lower() for role in roles if role and role.strip()]
    if len(normalized) < 2:
        raise click.ClickException("At least two roles are required for split-user conversion.")

    seen: list[str] = []
    for role in normalized:
        error = _validate_role_name(role, existing=seen)
        if error is not None:
            raise click.ClickException(error)
        seen.append(role)

    return normalized


def _validate_role_name(role: str, existing: Iterable[str]) -> str | None:
    if not role:
        return "Role name cannot be empty."
    if not ROLE_PATTERN.match(role):
        return "Role name must be lowercase snake_case and start with a letter."
    if role in RESERVED_ROLE_NAMES:
        return f"Role '{role}' is reserved and cannot be used for split targets."
    if role in set(existing):
        return f"Role '{role}' was already entered."
    return None


def _find_conflict_marker_files(root: Path, relative_paths: list[str]) -> list[str]:
    marker_pattern = re.compile(r"^(<<<<<<< |=======|>>>>>>> )", flags=re.MULTILINE)
    conflict_files: list[str] = []
    for relative in relative_paths:
        file_path = root / relative
        if not file_path.exists() or not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8")
        if marker_pattern.search(content):
            conflict_files.append(relative)
    return sorted(conflict_files)


def _collect_split_touch_files(roles: list[str]) -> list[str]:
    files = [
        "schemas/user_schema.py",
        "repositories/user_repo.py",
        "services/user_service.py",
        "api/v1/user_route.py",
        "security/auth.py",
        "security/principal.py",
        "security/account_status_check.py",
        "security/encrypting_jwt.py",
        "services/auth_helpers.py",
        "core/role_config.py",
        "repositories/tokens_repo.py",
        "main.py",
        ".env.example",
        "split_user_report.md",
        str(SPLIT_STATE_FILE).replace("\\", "/"),
    ]

    for role in roles:
        files.extend(
            [
                f"schemas/{role}_schema.py",
                f"repositories/{role}_repo.py",
                f"services/{role}_service.py",
                f"api/v1/{role}_route.py",
            ]
        )

    return sorted(set(files))


def _collect_unsplit_touch_files(split_roles: list[str]) -> list[str]:
    files = [
        "schemas/user_schema.py",
        "repositories/user_repo.py",
        "services/user_service.py",
        "api/v1/user_route.py",
        "security/auth.py",
        "security/principal.py",
        "security/account_status_check.py",
        "security/encrypting_jwt.py",
        "services/auth_helpers.py",
        "core/role_config.py",
        "repositories/tokens_repo.py",
        "main.py",
        ".env.example",
        "unsplit_user_report.md",
        str(SPLIT_STATE_FILE).replace("\\", "/"),
    ]

    for role in split_roles:
        files.extend(
            [
                f"schemas/{role}_schema.py",
                f"repositories/{role}_repo.py",
                f"services/{role}_service.py",
                f"api/v1/{role}_route.py",
            ]
        )

    return sorted(set(files))


def _archive_existing_files(root: Path, relative_paths: list[str], archive_root: Path) -> list[str]:
    archived: list[str] = []
    for relative in relative_paths:
        source = root / relative
        if not source.exists() or not source.is_file():
            continue

        destination = archive_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        archived.append(str(destination.relative_to(root)).replace("\\", "/"))

    return archived


def _ensure_required_sources(root: Path, required_paths: Iterable[Path]) -> None:
    missing = [str(path) for path in required_paths if not (root / path).exists()]
    if missing:
        raise click.ClickException(
            "Missing required user files for conversion: " + ", ".join(missing)
        )


def _write_role_runtime_files(root: Path, non_admin_roles: list[str]) -> None:
    normalized_non_admin_roles = [role.strip().lower() for role in non_admin_roles if role and role.strip()]
    if not normalized_non_admin_roles:
        normalized_non_admin_roles = ["user"]

    (root / "security" / "auth.py").write_text(
        _render_auth_py(normalized_non_admin_roles),
        encoding="utf-8",
    )
    (root / "security" / "principal.py").write_text(
        _render_principal_py(normalized_non_admin_roles),
        encoding="utf-8",
    )
    (root / "security" / "account_status_check.py").write_text(
        _render_account_status_check_py(normalized_non_admin_roles),
        encoding="utf-8",
    )
    (root / "services" / "auth_helpers.py").write_text(
        _render_auth_helpers_py(),
        encoding="utf-8",
    )
    (root / "security" / "encrypting_jwt.py").write_text(
        _render_encrypting_jwt_py(),
        encoding="utf-8",
    )

    role_config_path = root / "core" / "role_config.py"
    role_config_path.parent.mkdir(parents=True, exist_ok=True)
    role_config_path.write_text(_render_role_config_py(), encoding="utf-8")

    _rewrite_main_rate_limits(root / "main.py", normalized_non_admin_roles)


def _rewrite_main_rate_limits(main_file: Path, non_admin_roles: list[str]) -> None:
    content = main_file.read_text(encoding="utf-8")

    legacy_role_config_import = "from core.role_config import build_role_rate_limits, build_role_rate_limits_csv"
    role_config_import = (
        "from core.role_config import build_role_rate_limits, build_role_rate_limits_csv, normalize_role"
    )
    if legacy_role_config_import in content and role_config_import not in content:
        content = content.replace(legacy_role_config_import, role_config_import)
    if role_config_import not in content:
        anchor = "from core.settings import get_settings"
        if anchor in content:
            content = content.replace(anchor, f"{anchor}\n{role_config_import}")
        else:
            content = f"{role_config_import}\n{content}"

    default_roles_literal = ", ".join(f'\"{role}\"' for role in non_admin_roles)
    dynamic_block = (
        f"ROLE_RATE_LIMITS_DEFAULT = build_role_rate_limits_csv(non_admin_roles=[{default_roles_literal}])\n"
        "RATE_LIMITS = build_role_rate_limits(\n"
        "    os.getenv(\"ROLE_RATE_LIMITS\"),\n"
        "    fallback_csv=ROLE_RATE_LIMITS_DEFAULT,\n"
        ")\n\n"
        "storage = RedisStorage(settings.redis_url)"
    )

    content, replaced = re.subn(
        r"RATE_LIMITS\s*=\s*\{[\s\S]*?\}\n\nstorage\s*=\s*RedisStorage\(settings\.redis_url\)",
        dynamic_block,
        content,
        count=1,
    )

    if replaced == 0:
        content, replaced = re.subn(
            r"ROLE_RATE_LIMITS_DEFAULT\s*=\s*build_role_rate_limits_csv\([^\n]*\)",
            f"ROLE_RATE_LIMITS_DEFAULT = build_role_rate_limits_csv(non_admin_roles=[{default_roles_literal}])",
            content,
            count=1,
        )

    if replaced == 0:
        raise click.ClickException(
            "Unable to rewrite rate limit block in main.py. Expected FasterAPI template structure."
        )

    content = content.replace(
        'user_type = (access_token.role or "anonymous").lower()',
        'user_type = normalize_role(access_token.role or "anonymous")',
    )

    main_file.write_text(content, encoding="utf-8")


def _rewrite_role_specific_content(content: str, role: str) -> str:
    content = re.sub(r"\bverify_member_refresh_token\b", f"verify_{role}_refresh_token", content)
    content = re.sub(r"\bverify_user_refresh_token\b", f"verify_{role}_refresh_token", content)
    content = re.sub(r'role="member"', f'role="{role}"', content)
    content = re.sub(r'role="user"', f'role="{role}"', content)
    return content


def _write_state(root: Path, state: RoleSplitState) -> None:
    state_path = root / SPLIT_STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def _read_state(root: Path) -> RoleSplitState | None:
    state_path = root / SPLIT_STATE_FILE
    if not state_path.exists():
        return None

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return RoleSplitState(
        version=int(payload.get("version", 1)),
        mode=str(payload.get("mode", "unsplit")),
        roles=tuple(str(role) for role in payload.get("roles", [])),
        previous_primary_role=str(payload.get("previous_primary_role", "user")),
        created_at=str(payload.get("created_at", _iso_now())),
        touched_files=tuple(str(path) for path in payload.get("touched_files", [])),
        archived_at=payload.get("archived_at"),
        last_unsplit_at=payload.get("last_unsplit_at"),
    )


def _detect_split_roles(root: Path) -> list[str]:
    routes_dir = root / "api" / "v1"
    if not routes_dir.exists():
        return []

    excluded_routes = {"__init__", "admin", "user", "payments", "documents"}
    detected: list[str] = []

    for route_file in sorted(routes_dir.glob("*_route.py")):
        role = route_file.stem.removesuffix("_route")
        if role in excluded_routes:
            continue

        required_files = [
            root / "schemas" / f"{role}_schema.py",
            root / "repositories" / f"{role}_repo.py",
            root / "services" / f"{role}_service.py",
        ]
        if all(path.exists() for path in required_files):
            detected.append(role)

    return detected


def _upsert_env_var(file_path: Path, key: str, value: str) -> None:
    line = f"{key}={value}"

    if file_path.exists():
        lines = file_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated = False
    new_lines: list[str] = []
    for current in lines:
        if current.startswith(f"{key}="):
            new_lines.append(line)
            updated = True
        else:
            new_lines.append(current)

    if not updated:
        new_lines.append(line)

    file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _build_role_rate_limits_csv(non_admin_roles: list[str]) -> str:
    role_parts = [f"anonymous:{DEFAULT_ANONYMOUS_RATE}"]
    role_parts.extend(f"{role}:{DEFAULT_ROLE_RATE}" for role in non_admin_roles)
    role_parts.append(f"admin:{DEFAULT_ADMIN_RATE}")
    return ",".join(role_parts)


def _write_report(path: Path, title: str, body_lines: list[str]) -> None:
    lines = [
        f"# {title}",
        "",
        f"Generated at: {_iso_now()}",
        "",
        "## Summary",
    ]
    lines.extend(f"- {line}" for line in body_lines)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _humanize_roles(roles: list[str]) -> str:
    if len(roles) == 1:
        return roles[0]
    if len(roles) == 2:
        return f"{roles[0]} and {roles[1]}"
    return ", ".join(roles[:-1]) + f", and {roles[-1]}"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _render_auth_py(non_admin_roles: list[str]) -> str:
    auth_roles = [*non_admin_roles, "admin"]
    first_role = non_admin_roles[0]
    token_alias_target = "user" if "user" in non_admin_roles else first_role

    verify_token_alias = f"verify_{token_alias_target}_token"
    verify_refresh_alias = f"verify_{token_alias_target}_refresh_token"

    role_verifiers: list[str] = []
    refresh_verifiers: list[str] = []
    for role in non_admin_roles:
        role_verifiers.append(
            f"""
async def verify_{role}_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    principal = await _resolve_principal(credentials, allow_expired=False)
    if principal.role != \"{role}\":
        raise auth_role_mismatch(required_role=\"{role}\", actual_role=principal.role)
    return principal
""".strip()
        )
        refresh_verifiers.append(
            f"""
async def verify_{role}_refresh_token(
    principal: AuthPrincipal = Depends(verify_token_to_refresh),
) -> AuthPrincipal:
    if principal.role != \"{role}\":
        raise auth_role_mismatch(required_role=\"{role}\", actual_role=principal.role)
    return principal
""".strip()
        )

    return f'''from __future__ import annotations

from typing import Final

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.errors import auth_invalid_token, auth_role_mismatch
from repositories.tokens_repo import get_access_token, get_access_token_allow_expired
from security.principal import AuthPrincipal


token_auth_scheme = HTTPBearer(auto_error=True)
AUTH_ROLES: Final[tuple[str, ...]] = ({", ".join(repr(role) for role in auth_roles)},)
NON_ADMIN_ROLES: Final[tuple[str, ...]] = ({", ".join(repr(role) for role in non_admin_roles)},)
LEGACY_ROLE_ALIASES: Final[dict[str, str]] = {{"member": "user"}}


def _normalize_role(role: str | None) -> str:
    value = (role or "").lower()
    return LEGACY_ROLE_ALIASES.get(value, value)


async def _resolve_principal(
    credentials: HTTPAuthorizationCredentials,
    *,
    allow_expired: bool,
) -> AuthPrincipal:
    getter = get_access_token_allow_expired if allow_expired else get_access_token
    token_record = await getter(accessToken=credentials.credentials)
    if token_record is None:
        raise auth_invalid_token()

    role = _normalize_role(token_record.role)
    if role not in AUTH_ROLES:
        raise auth_invalid_token(details={{"role": token_record.role}})

    return AuthPrincipal(
        user_id=token_record.userId,
        role=role,
        access_token_id=token_record.accesstoken,
        jwt_token=credentials.credentials,
        allow_expired=allow_expired,
    )


async def verify_any_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await _resolve_principal(credentials, allow_expired=False)


{chr(10).join(role_verifiers)}


async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    principal = await _resolve_principal(credentials, allow_expired=False)
    if principal.role != "admin":
        raise auth_role_mismatch(required_role="admin", actual_role=principal.role)
    return principal


async def verify_token_to_refresh(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await _resolve_principal(credentials, allow_expired=True)


{chr(10).join(refresh_verifiers)}


async def verify_admin_refresh_token(
    principal: AuthPrincipal = Depends(verify_token_to_refresh),
) -> AuthPrincipal:
    if principal.role != "admin":
        raise auth_role_mismatch(required_role="admin", actual_role=principal.role)
    return principal


# Backward-compatible aliases
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await {verify_token_alias}(credentials)


async def verify_member_refresh_token(
    principal: AuthPrincipal = Depends(verify_token_to_refresh),
) -> AuthPrincipal:
    return await {verify_refresh_alias}(principal)


async def verify_token_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await verify_token(credentials)


async def verify_admin_token_otp(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await verify_admin_token(credentials)
'''


def _render_principal_py(non_admin_roles: list[str]) -> str:
    all_roles = [*non_admin_roles, "admin"]

    role_properties = [
        f"""
    @property
    def is_{role}(self) -> bool:
        return self.role == "{role}"
""".rstrip()
        for role in non_admin_roles
    ]

    member_alias = ""
    if "user" in non_admin_roles:
        member_alias = """

    @property
    def is_member(self) -> bool:
        return self.role == "user"
"""

    return f'''from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AuthPrincipal(BaseModel):
    user_id: str
    role: Literal[{", ".join(repr(role) for role in all_roles)}]
    access_token_id: str
    jwt_token: str
    allow_expired: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

{chr(10).join(role_properties)}{member_alias}
'''


def _render_account_status_check_py(non_admin_roles: list[str]) -> str:
    role_functions: list[str] = []
    for role in non_admin_roles:
        role_functions.append(
            f"""
async def check_{role}_account_status_and_permissions(
    request: Request,
    principal: AuthPrincipal = Depends(verify_{role}_token),
):
    return await _check_non_admin_account_status_and_permissions(
        request=request,
        principal=principal,
        role="{role}",
    )
""".strip()
        )

    member_alias = ""
    if "user" in non_admin_roles:
        member_alias = """

async def check_member_account_status_and_permissions(
    request: Request,
    principal: AuthPrincipal = Depends(verify_user_token),
):
    return await check_user_account_status_and_permissions(request=request, principal=principal)
"""

    return f'''from __future__ import annotations

from importlib import import_module

from fastapi import Depends, Request, status

from core.errors import AppException, ErrorCode, auth_permission_denied
from schemas.imports import AccountStatus, PermissionList
from security.auth import verify_admin_token, {", ".join(f"verify_{role}_token" for role in non_admin_roles)}
from security.permissions import make_permission_key
from security.principal import AuthPrincipal
from services.admin_service import retrieve_admin_by_admin_id


def _validate_permission_list(permission_list: PermissionList | None) -> None:
    if permission_list is None or not permission_list.permissions:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AUTH_PERMISSION_DENIED,
            message="No permissions assigned",
        )

    seen: set[str] = set()
    for permission in permission_list.permissions:
        if permission.key:
            if permission.key in seen:
                raise AppException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Duplicate permission key configuration",
                    details={{"key": permission.key}},
                )
            seen.add(permission.key)


def _has_permission(
    *,
    permission_list: PermissionList,
    permission_key: str,
    endpoint_name: str,
    request_method: str,
) -> bool:
    for permission in permission_list.permissions:
        if permission.key and permission.key == permission_key:
            return True

        if permission.name == endpoint_name and request_method in permission.methods:
            return True

    return False


def _build_permission_context(request: Request) -> tuple[str, str, str]:
    endpoint = request.scope.get("endpoint")
    endpoint_name = endpoint.__name__ if endpoint else "unknown"
    request_method = request.method.upper()
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    permission_key = make_permission_key(method=request_method, path=route_path)
    return endpoint_name, request_method, permission_key


async def _check_non_admin_account_status_and_permissions(
    *,
    request: Request,
    principal: AuthPrincipal,
    role: str,
):
    module = import_module(f"services.{{role}}_service")
    fetcher = getattr(module, f"retrieve_{{role}}_by_{{role}}_id", None)
    if fetcher is None:
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.INTERNAL_ERROR,
            message="Missing role retrieval function",
            details={{"role": role}},
        )

    account = await fetcher(id=principal.user_id)
    if not account:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_PRINCIPAL_NOT_FOUND,
            message=f"{{role.capitalize()}} not found",
        )

    if account.accountStatus != AccountStatus.ACTIVE:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AUTH_ACCOUNT_INACTIVE,
            message=f"{{role.capitalize()}} account is not active",
        )

    endpoint_name, request_method, permission_key = _build_permission_context(request)
    permission_list = getattr(account, "permissionList", None)
    _validate_permission_list(permission_list)

    if not _has_permission(
        permission_list=permission_list,
        permission_key=permission_key,
        endpoint_name=endpoint_name,
        request_method=request_method,
    ):
        raise auth_permission_denied(permission_key)

    return account


async def check_admin_account_status_and_permissions(
    request: Request,
    principal: AuthPrincipal = Depends(verify_admin_token),
):
    admin = await retrieve_admin_by_admin_id(id=principal.user_id)
    if not admin:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_PRINCIPAL_NOT_FOUND,
            message="Admin not found",
        )

    if admin.accountStatus != AccountStatus.ACTIVE:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AUTH_ACCOUNT_INACTIVE,
            message="Admin account is not active",
        )

    endpoint_name, request_method, permission_key = _build_permission_context(request)
    permission_list = getattr(admin, "permissionList", None)
    _validate_permission_list(permission_list)

    if not _has_permission(
        permission_list=permission_list,
        permission_key=permission_key,
        endpoint_name=endpoint_name,
        request_method=request_method,
    ):
        raise auth_permission_denied(permission_key)

    return admin


{chr(10).join(role_functions)}{member_alias}
'''


def _render_auth_helpers_py() -> str:
    return '''from __future__ import annotations

from fastapi import HTTPException, status

from repositories import tokens_repo as token_repo
from schemas.tokens_schema import accessTokenCreate, refreshTokenCreate
from security.encrypting_jwt import create_jwt_role_token


LEGACY_ROLE_ALIASES = {"member": "user"}


def _normalize_role(role: str) -> str:
    return LEGACY_ROLE_ALIASES.get(role.strip().lower(), role.strip().lower())


async def _issue_access_token(user_id: str, role: str):
    role = _normalize_role(role)
    role_function = f"add_{role}_access_token"
    add_token = getattr(token_repo, role_function, None)

    if add_token is None:
        if role == "user":
            add_token = getattr(token_repo, "add_access_tokens", None)
        elif role == "admin":
            add_token = getattr(token_repo, "add_admin_access_tokens", None)

    if add_token is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Token repository role function not found",
                "role": role,
                "expected_function": role_function,
            },
        )

    return await add_token(token_data=accessTokenCreate(userId=user_id))


async def issue_tokens_for_role(user_id: str, role: str) -> tuple[str, str]:
    normalized_role = _normalize_role(role)
    access_token = await _issue_access_token(user_id=user_id, role=normalized_role)

    jwt_token = await create_jwt_role_token(
        token=access_token.accesstoken,
        user_id=user_id,
        role=normalized_role,
    )

    refresh_token = await token_repo.add_refresh_tokens(
        token_data=refreshTokenCreate(
            userId=user_id,
            previousAccessToken=access_token.accesstoken,
        )
    )

    return jwt_token, refresh_token.refreshtoken


async def issue_tokens_for_user(user_id: str, role: str) -> tuple[str, str]:
    return await issue_tokens_for_role(user_id=user_id, role=role)
'''


def _render_encrypting_jwt_py() -> str:
    return '''import os
from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from dotenv import load_dotenv
from pydantic import BaseModel

from core.database import db
from core.settings import get_settings

load_dotenv()
SECRETID = os.getenv("SECRETID")

# Token lifetime (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class JWTPayload(BaseModel):
    access_token: str
    user_id: str
    user_type: str
    is_activated: bool
    exp: datetime
    iat: datetime


SECRET_KEY = get_settings().secret_key or "dev-only-insecure-secret"
ALGORITHM = "HS256"


async def get_secret_dict() -> dict:
    result = await db.secret_keys.find_one({"_id": ObjectId(SECRETID)})
    result.pop("_id")
    return result


async def get_secret_and_header():
    import random

    secrets = await get_secret_dict()

    random_key = random.choice(list(secrets.keys()))
    random_secret = secrets[random_key]
    secret_keys = {random_key: random_secret}
    headers = {"kid": random_key}
    return {
        "SECRET_KEY": secret_keys,
        "HEADERS": headers,
    }


def create_jwt_token(
    access_token: str,
    user_id: str,
    user_type: str,
    is_activated: bool,
    role: str = "user",
) -> str:
    payload = JWTPayload(
        access_token=access_token,
        user_id=user_id,
        user_type=user_type,
        is_activated=is_activated,
        exp=datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        iat=datetime.now(timezone.utc),
    ).model_dump()

    payload["role"] = role

    token = jwt.encode(
        payload=payload,
        key=SECRET_KEY,
        algorithm=ALGORITHM,
        headers={"typ": "JWT"},
    )
    return token


async def create_jwt_role_token(token: str, user_id: str, role: str) -> str:
    payload = {
        "accessToken": token,
        "role": role,
        "userId": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_jwt_user_token(token: str, userId: str):
    return await create_jwt_role_token(token=token, user_id=userId, role="user")


async def create_jwt_member_token(token: str, userId: str):
    return await create_jwt_user_token(token=token, userId=userId)


async def create_jwt_admin_token(token: str, userId: str):
    return await create_jwt_role_token(token=token, user_id=userId, role="admin")


async def decode_jwt_token(token: str):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except jwt.ExpiredSignatureError:
        print("Expired token")
        return None
    except jwt.InvalidSignatureError:
        print("Invalid signature")
        return None
    except jwt.DecodeError:
        print("Malformed token")
        return None
    except Exception as exc:
        print(f"Unexpected decode error: {exc}")
        return None


async def decode_jwt_token_without_expiration(token: str):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except jwt.ExpiredSignatureError:
        try:
            decoded = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_exp": False},
            )
            return decoded
        except Exception as inner_exc:
            print(f"Failed to decode expired token: {inner_exc}")
            return None
    except jwt.DecodeError:
        print("Malformed token")
        return None
    except Exception as exc:
        print(f"Unexpected error decoding token: {exc}")
        return None
'''


def _render_role_config_py() -> str:
    return '''from __future__ import annotations

from collections.abc import Sequence

from limits import parse as parse_rate


DEFAULT_ANONYMOUS_RATE = "20/minute"
DEFAULT_ROLE_RATE = "80/minute"
DEFAULT_ADMIN_RATE = "140/minute"

LEGACY_ROLE_ALIASES = {"member": "user"}


def normalize_role(role: str | None) -> str:
    value = (role or "anonymous").strip().lower() or "anonymous"
    return LEGACY_ROLE_ALIASES.get(value, value)


def build_role_rate_limits_csv(non_admin_roles: Sequence[str], include_admin: bool = True) -> str:
    entries = [f"anonymous:{DEFAULT_ANONYMOUS_RATE}"]
    entries.extend(f"{normalize_role(role)}:{DEFAULT_ROLE_RATE}" for role in non_admin_roles)
    if include_admin:
        entries.append(f"admin:{DEFAULT_ADMIN_RATE}")
    return ",".join(entries)


def parse_role_rate_limits(raw: str | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not raw:
        return parsed

    for entry in raw.split(","):
        value = entry.strip()
        if not value or ":" not in value:
            continue
        role, limit = value.split(":", 1)
        role_key = normalize_role(role)
        limit_value = limit.strip()
        if role_key and limit_value:
            parsed[role_key] = limit_value

    return parsed


def build_role_rate_limits(raw: str | None, *, fallback_csv: str):
    configured = parse_role_rate_limits(raw)
    fallback = parse_role_rate_limits(fallback_csv)

    selected = configured or fallback
    if "anonymous" not in selected:
        selected["anonymous"] = DEFAULT_ANONYMOUS_RATE
    if "admin" not in selected:
        selected["admin"] = DEFAULT_ADMIN_RATE

    final_limits = {}
    for role, rule in selected.items():
        try:
            final_limits[role] = parse_rate(rule)
        except Exception:
            # Skip invalid per-role rules and rely on anonymous fallback.
            continue

    if "anonymous" not in final_limits:
        final_limits["anonymous"] = parse_rate(DEFAULT_ANONYMOUS_RATE)

    return final_limits
'''
