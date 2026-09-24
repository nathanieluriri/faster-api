from __future__ import annotations

import ast
import keyword
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Sequence

import click

from fasterapi.scaffolder.project_python import project_python


@dataclass(frozen=True)
class TemplateExample:
    key: str
    filename: str
    title: str
    description: str
    category: str


@dataclass(frozen=True)
class TemplateSpec:
    path: Path
    module_name: str
    template_key: str
    subject: str


EXAMPLES: tuple[TemplateExample, ...] = (
    TemplateExample(
        key="changing-password",
        filename="changing_password_template.py",
        title="Password Changed",
        description="Notifies a user when their password is changed.",
        category="security",
    ),
    TemplateExample(
        key="invitation",
        filename="invitation_template.py",
        title="Team Invitation",
        description="Invites a user to collaborate on a project.",
        category="account",
    ),
    TemplateExample(
        key="new-signin",
        filename="new_sign_in.py",
        title="New Sign-In Alert",
        description="Warns users about a new account sign-in.",
        category="security",
    ),
    TemplateExample(
        key="otp",
        filename="otp_template.py",
        title="Login OTP",
        description="Sends a one-time passcode for sign-in.",
        category="security",
    ),
    TemplateExample(
        key="revoking",
        filename="revoking_template.py",
        title="Invitation Revoked",
        description="Informs a user that access has been revoked.",
        category="account",
    ),
    TemplateExample(
        key="welcome",
        filename="welcome_template.py",
        title="Welcome",
        description="Greets new users after registration.",
        category="onboarding",
    ),
    TemplateExample(
        key="password-reset",
        filename="password_reset_template.py",
        title="Password Reset",
        description="Sends a secure password reset link.",
        category="security",
    ),
    TemplateExample(
        key="email-verification",
        filename="email_verification_template.py",
        title="Email Verification",
        description="Confirms ownership of a user's email address.",
        category="onboarding",
    ),
    TemplateExample(
        key="receipt",
        filename="receipt_template.py",
        title="Payment Receipt",
        description="Confirms successful payment for an order.",
        category="billing",
    ),
    TemplateExample(
        key="account-deactivated",
        filename="account_deactivated_template.py",
        title="Account Deactivated",
        description="Notifies users when an account is disabled.",
        category="account",
    ),
)


def _builtin_templates_root() -> Path:
    return Path(__file__).parent / "templates" / "email_examples"


def _project_root() -> Path:
    return Path.cwd()


def _email_templates_dir() -> Path:
    return _project_root() / "email_templates"


def _custom_templates_dir() -> Path:
    return _project_root() / "custom_templates"


def _mount_file_path() -> Path:
    return _project_root() / "core" / "email" / "mounted_templates.py"


def _mount_error_file_path() -> Path:
    return _project_root() / "email_mount_errors.log"


def _ensure_template_dirs() -> bool:
    if not (_project_root() / "main.py").exists() or not (_project_root() / "core").is_dir():
        click.secho("Run this from a FasterAPI project root (main.py and core/ are required).", fg="red")
        return False
    email_dir = _email_templates_dir()
    custom_dir = _custom_templates_dir()
    core_email_dir = _project_root() / "core" / "email"

    email_dir.mkdir(parents=True, exist_ok=True)
    custom_dir.mkdir(parents=True, exist_ok=True)
    core_email_dir.mkdir(parents=True, exist_ok=True)

    init_file = email_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")
    return True



def _extract_assigned_string(module: ast.Module, variable_name: str) -> str | None:
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == variable_name:
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    return node.value.value
    return None



def _has_renderer_function(module: ast.Module, function_name: str) -> bool:
    # The manager calls render_x(context) synchronously, so it must be a plain def taking one positional argument.
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return len(node.args.posonlyargs) + len(node.args.args) > 0
    return False



def _validate_template_file(path: Path) -> tuple[TemplateSpec | None, list[str]]:
    errors: list[str] = []
    if not path.stem.isidentifier() or keyword.iskeyword(path.stem):
        errors.append(
            f"{path.name}: filename is not a valid Python module name; use letters, numbers, and underscores "
            "only, and not a Python keyword"
        )
        return None, errors

    try:
        # Parsing bytes lets Python honour a BOM or a coding declaration, as it does on import.
        parsed = ast.parse(path.read_bytes(), filename=str(path))
    except (OSError, SyntaxError, ValueError) as exc:
        return None, [f"{path.name}: failed to parse template ({exc})"]

    template_key = _extract_assigned_string(parsed, "TEMPLATE_KEY")
    if not template_key:
        errors.append(f"{path.name}: missing string constant TEMPLATE_KEY")

    subject = _extract_assigned_string(parsed, "SUBJECT")
    if not subject:
        errors.append(f"{path.name}: missing string constant SUBJECT")

    if not _has_renderer_function(parsed, "render_html"):
        errors.append(f"{path.name}: missing render_html(context) function (a regular def, not async)")

    if not _has_renderer_function(parsed, "render_text"):
        errors.append(f"{path.name}: missing render_text(context) function (a regular def, not async)")

    if errors:
        return None, errors

    return (
        TemplateSpec(
            path=path,
            module_name=path.stem,
            template_key=template_key or "",
            subject=subject or "",
        ),
        [],
    )



def _discover_template_specs() -> tuple[list[TemplateSpec], list[str]]:
    template_dir = _email_templates_dir()
    errors: list[str] = []
    specs: list[TemplateSpec] = []

    template_files = sorted(
        path for path in template_dir.glob("*.py") if path.name != "__init__.py"
    )

    if not template_files:
        click.secho("No templates in email_templates/; mounting none. Add one with 'fasterapi email add-template'.", fg="yellow")
        return [], []

    for template_file in template_files:
        spec, file_errors = _validate_template_file(template_file)
        if file_errors:
            errors.extend(file_errors)
            continue
        if spec is not None:
            specs.append(spec)

    seen_template_keys: dict[str, str] = {}
    for spec in specs:
        normalized_key = spec.template_key.lower()
        if normalized_key in seen_template_keys:
            first_module = seen_template_keys[normalized_key]
            errors.append(
                "Duplicate TEMPLATE_KEY "
                f"'{spec.template_key}' found in {first_module}.py and {spec.module_name}.py"
            )
        else:
            seen_template_keys[normalized_key] = spec.module_name

    return specs, errors



def _generate_mounted_templates_module(specs: Sequence[TemplateSpec]) -> str:
    modules = "".join(f'    "email_templates.{spec.module_name}",\n' for spec in specs)
    return f'''from __future__ import annotations

import logging
from importlib import import_module

from core.email.types import MountedTemplate

# Generated by `fasterapi email mount`. Each template is imported on its own, so one broken template
# is logged and skipped instead of disabling every email.
_MODULES = [
{modules}]


def get_mounted_templates() -> list[MountedTemplate]:
    templates: list[MountedTemplate] = []
    for name in _MODULES:
        try:
            module = import_module(name)
        except Exception:
            logging.getLogger(__name__).exception("Email template module %s failed to import", name)
            continue
        templates.append(
            MountedTemplate(
                key=module.TEMPLATE_KEY,
                subject=module.SUBJECT,
                render_html=module.render_html,
                render_text=module.render_text,
            )
        )
    return templates
'''



def _write_mount_error_log(errors: Sequence[str]) -> Path:
    log_path = _mount_error_file_path()
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    content = [f"Email mount failed at {timestamp} UTC", "", "Errors:"]
    content.extend(f"- {error}" for error in errors)
    content.append("")
    log_path.write_text("\n".join(content), encoding="utf-8")
    return log_path



def _remove_mount_error_log_if_present() -> None:
    log_path = _mount_error_file_path()
    if log_path.exists():
        log_path.unlink()



def list_template_examples() -> tuple[TemplateExample, ...]:
    return EXAMPLES



def add_email_template(*, template_key: str | None = None, force: bool = False) -> bool:
    if not _ensure_template_dirs():
        return False

    examples_by_key = {example.key: example for example in EXAMPLES}
    selected_example: TemplateExample | None = None

    if template_key:
        selected_example = examples_by_key.get(template_key.lower())
        if selected_example is None:
            click.secho(
                f"Unknown template key '{template_key}'. Available keys: {', '.join(sorted(examples_by_key))}",
                fg="red",
            )
            return False
    else:
        categories = sorted({example.category for example in EXAMPLES})
        template_type = click.prompt(
            "What kind of template do you need",
            type=click.Choice(categories, case_sensitive=False),
            show_choices=True,
        )

        click.secho("Available template examples:", fg="cyan")
        for example in EXAMPLES:
            click.secho(
                f"  - {example.key} [{example.category}] - {example.title}: {example.description}",
                fg="white",
            )

        scoped_examples = [
            example for example in EXAMPLES if example.category.lower() == template_type.lower()
        ]

        click.secho(f"Templates matching '{template_type}':", fg="cyan")
        for example in scoped_examples:
            click.secho(
                f"  - {example.key}: {example.title} ({example.description})",
                fg="white",
            )

        selected_key = click.prompt(
            "Select template example",
            type=click.Choice([example.key for example in scoped_examples], case_sensitive=False),
            show_choices=False,
        )
        selected_example = examples_by_key[selected_key]

    source = _builtin_templates_root() / selected_example.filename
    if not source.exists():
        click.secho(f"Template source not found: {source}", fg="red")
        return False

    destination = _email_templates_dir() / selected_example.filename
    if destination.exists() and not force:
        click.secho(
            f"Template already exists: {destination}. Use --force to overwrite.",
            fg="yellow",
        )
        return False

    shutil.copy2(source, destination)
    click.secho(
        f"Template '{selected_example.key}' added to email_templates/{selected_example.filename}",
        fg="green",
    )
    send_key = _extract_assigned_string(ast.parse(destination.read_bytes()), "TEMPLATE_KEY")
    if send_key:
        click.secho(f"Send it with template_key=\"{send_key}\".", fg="cyan")
    click.secho("Run 'fasterapi email mount' to register this template.", fg="cyan")
    return True



def mount_email_templates(*, extra_errors: Sequence[str] | None = None) -> bool:
    if not _ensure_template_dirs():
        return False

    specs, errors = _discover_template_specs()
    combined_errors = list(errors)
    if extra_errors:
        combined_errors.extend(extra_errors)

    if combined_errors:
        log_path = _write_mount_error_log(combined_errors)
        click.secho(
            "Email template mount failed. Check email_mount_errors.log for details.",
            fg="red",
        )
        click.secho(f"Log file: {log_path}", fg="yellow")
        return False

    mount_file = _mount_file_path()
    mount_file.parent.mkdir(parents=True, exist_ok=True)
    previous = mount_file.read_text(encoding="utf-8") if mount_file.exists() else None
    mount_file.write_text(_generate_mounted_templates_module(specs), encoding="utf-8")

    import_error = _mounted_templates_import_error()
    if import_error and not _is_missing_third_party_module(import_error):
        if previous is None:
            mount_file.unlink()
        else:
            mount_file.write_text(previous, encoding="utf-8")
        log_path = _write_mount_error_log([f"Mounted templates failed to import: {import_error}"])
        click.secho("Email template mount failed: the templates don't import cleanly.", fg="red")
        click.secho(f"Log file: {log_path}", fg="yellow")
        return False
    if import_error:
        click.secho(
            f"Couldn't verify the templates import ({import_error}); install the project's requirements to check.",
            fg="yellow",
        )
    _remove_mount_error_log_if_present()
    click.secho(
        f"Mounted {len(specs)} email template(s) into core/email/mounted_templates.py",
        fg="green",
    )
    return True



def _mounted_templates_import_error() -> str | None:
    completed = subprocess.run(
        [project_python(), "-c", "import importlib; from core.email.mounted_templates import _MODULES; [importlib.import_module(m) for m in _MODULES]"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode == 0:
        return None
    return (completed.stderr.strip().splitlines() or ["unknown import error"])[-1]


def _is_missing_third_party_module(error: str) -> bool:
    missing = re.search(r"No module named '([^']+)'", error)
    return bool(missing) and not missing.group(1).startswith(("core", "email_templates"))


def mount_custom_email_templates(*, force: bool = False) -> bool:
    if not _ensure_template_dirs():
        return False

    custom_files = sorted(
        path for path in _custom_templates_dir().glob("*.py") if path.name != "__init__.py"
    )
    if not custom_files:
        click.secho("No custom templates found in custom_templates/", fg="yellow")
        return mount_email_templates()

    pre_mount_errors: list[str] = []
    moved_files: list[str] = []

    for custom_file in custom_files:
        spec, validation_errors = _validate_template_file(custom_file)
        pre_mount_errors.extend(validation_errors)
        destination = _email_templates_dir() / custom_file.name
        if not validation_errors and destination.exists() and not force:
            pre_mount_errors.append(
                f"{custom_file.name}: destination already exists in email_templates/ (use --force to overwrite)"
            )

    # Move nothing unless every custom template is valid, so a failed run leaves the folders as they were.
    if pre_mount_errors:
        return mount_email_templates(extra_errors=pre_mount_errors)

    for custom_file in custom_files:
        destination = _email_templates_dir() / custom_file.name
        if destination.exists():
            destination.unlink()
        shutil.move(str(custom_file), str(destination))
        moved_files.append(destination.name)

    if moved_files:
        click.secho(
            f"Moved {len(moved_files)} custom template(s) into email_templates/: {', '.join(moved_files)}",
            fg="green",
        )

    return mount_email_templates(extra_errors=pre_mount_errors)
