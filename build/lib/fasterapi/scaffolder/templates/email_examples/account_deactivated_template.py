from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "account_deactivated"
SUBJECT = "Account deactivated"


def render_html(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    reason = str(context.get("reason", "Policy review"))
    support_email = str(context.get("support_email", "support@example.com"))
    return (
        "<h2>Account Deactivated</h2>"
        f"<p>Hello {user_name}, your account was deactivated.</p>"
        f"<p>Reason: {reason}</p>"
        f"<p>Contact support: <a href='mailto:{support_email}'>{support_email}</a></p>"
    )


def render_text(context: dict[str, Any]) -> str:
    reason = str(context.get("reason", "Policy review"))
    support_email = str(context.get("support_email", "support@example.com"))
    return f"Your account was deactivated. Reason: {reason}. Contact {support_email}."
