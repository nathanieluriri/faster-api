from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "password_reset"
SUBJECT = "Reset your password"


def render_html(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    reset_link = str(context.get("reset_link", "#"))
    expires_in = str(context.get("expires_in", "30 minutes"))
    return (
        "<h2>Password Reset</h2>"
        f"<p>Hello {user_name},</p>"
        f"<p><a href='{reset_link}'>Reset your password</a></p>"
        f"<p>This link expires in {expires_in}.</p>"
    )


def render_text(context: dict[str, Any]) -> str:
    reset_link = str(context.get("reset_link", "#"))
    expires_in = str(context.get("expires_in", "30 minutes"))
    return f"Reset your password here: {reset_link}. Link expires in {expires_in}."
