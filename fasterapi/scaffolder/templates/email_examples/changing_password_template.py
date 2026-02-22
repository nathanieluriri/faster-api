from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "changing_password"
SUBJECT = "Your password was changed"


def render_html(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    changed_at = str(context.get("changed_at", "just now"))
    support_email = str(context.get("support_email", "support@example.com"))
    return (
        "<h2>Password Changed</h2>"
        f"<p>Hello {user_name},</p>"
        f"<p>Your password was changed on <strong>{changed_at}</strong>.</p>"
        f"<p>If this was not you, contact <a href='mailto:{support_email}'>{support_email}</a> immediately.</p>"
    )


def render_text(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    changed_at = str(context.get("changed_at", "just now"))
    support_email = str(context.get("support_email", "support@example.com"))
    return (
        f"Hello {user_name}, your password was changed on {changed_at}. "
        f"If this was not you, contact {support_email}."
    )
