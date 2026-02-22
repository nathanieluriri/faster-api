from __future__ import annotations

import ast
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Sequence

import click


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


def _ensure_template_dirs() -> None:
    email_dir = _email_templates_dir()
    custom_dir = _custom_templates_dir()
    core_email_dir = _project_root() / "core" / "email"

    email_dir.mkdir(parents=True, exist_ok=True)
    custom_dir.mkdir(parents=True, exist_ok=True)
    core_email_dir.mkdir(parents=True, exist_ok=True)

    init_file = email_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")



def _sanitize_alias(name: str) -> str:
    safe = re.sub(r"\W+", "_", name)
    if safe and safe[0].isdigit():
        safe = f"template_{safe}"
    return safe.lower() or "template_alias"



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
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            positional_args = len(node.args.args)
            kwonly_args = len(node.args.kwonlyargs)
            return positional_args + kwonly_args > 0
    return False



def _validate_template_file(path: Path) -> tuple[TemplateSpec | None, list[str]]:
    errors: list[str] = []
    if not path.stem.isidentifier():
        errors.append(
            f"{path.name}: filename is not a valid Python module name; use letters, numbers, and underscores only"
        )
        return None, errors

    try:
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return None, [f"{path.name}: failed to parse template ({exc})"]

    template_key = _extract_assigned_string(parsed, "TEMPLATE_KEY")
    if not template_key:
        errors.append(f"{path.name}: missing string constant TEMPLATE_KEY")

    subject = _extract_assigned_string(parsed, "SUBJECT")
    if not subject:
        errors.append(f"{path.name}: missing string constant SUBJECT")

    if not _has_renderer_function(parsed, "render_html"):
        errors.append(f"{path.name}: missing render_html(context) function")

    if not _has_renderer_function(parsed, "render_text"):
        errors.append(f"{path.name}: missing render_text(context) function")

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
        return [], [
            "No templates were found in email_templates/. Add one with 'fasterapi email add-template'."
        ]

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
    import_lines: list[str] = [
        "from __future__ import annotations",
        "",
        "from core.email.types import MountedTemplate",
    ]

    entry_lines: list[str] = []

    for spec in specs:
        alias = _sanitize_alias(spec.module_name)
        import_lines.append(
            f"from email_templates.{spec.module_name} import SUBJECT as {alias}_subject"
        )
        import_lines.append(
            f"from email_templates.{spec.module_name} import TEMPLATE_KEY as {alias}_key"
        )
        import_lines.append(
            f"from email_templates.{spec.module_name} import render_html as {alias}_render_html"
        )
        import_lines.append(
            f"from email_templates.{spec.module_name} import render_text as {alias}_render_text"
        )
        entry_lines.extend(
            [
                "        MountedTemplate(",
                f"            key={alias}_key,",
                f"            subject={alias}_subject,",
                f"            render_html={alias}_render_html,",
                f"            render_text={alias}_render_text,",
                "        ),",
            ]
        )

    if specs:
        import_lines.append("")
        body = [
            "def get_mounted_templates() -> list[MountedTemplate]:",
            "    return [",
            *entry_lines,
            "    ]",
            "",
        ]
    else:
        import_lines.append("")
        body = [
            "def get_mounted_templates() -> list[MountedTemplate]:",
            "    return []",
            "",
        ]

    return "\n".join(import_lines + body)



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
    _ensure_template_dirs()

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
    click.secho("Run 'fasterapi email mount' to register this template.", fg="cyan")
    return True



def mount_email_templates(*, extra_errors: Sequence[str] | None = None) -> bool:
    _ensure_template_dirs()

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
    mount_file.write_text(_generate_mounted_templates_module(specs), encoding="utf-8")
    _remove_mount_error_log_if_present()
    click.secho(
        f"Mounted {len(specs)} email template(s) into core/email/mounted_templates.py",
        fg="green",
    )
    return True



def mount_custom_email_templates(*, force: bool = False) -> bool:
    _ensure_template_dirs()

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
        if validation_errors:
            pre_mount_errors.extend(validation_errors)
            continue

        destination = _email_templates_dir() / custom_file.name
        if destination.exists() and not force:
            pre_mount_errors.append(
                f"{custom_file.name}: destination already exists in email_templates/ (use --force to overwrite)"
            )
            continue

        if destination.exists() and force:
            destination.unlink()

        shutil.move(str(custom_file), str(destination))
        moved_files.append(destination.name)

    if moved_files:
        click.secho(
            f"Moved {len(moved_files)} custom template(s) into email_templates/: {', '.join(moved_files)}",
            fg="green",
        )

    return mount_email_templates(extra_errors=pre_mount_errors)
