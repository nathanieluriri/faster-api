from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "email_verification"
SUBJECT = "Verify your email"


def render_html(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    verification_link = str(context.get("verification_link", "#"))
    return (
        "<h2>Email Verification</h2>"
        f"<p>Hello {user_name}, please verify your email address.</p>"
        f"<p><a href='{verification_link}'>Verify email</a></p>"
    )


def render_text(context: dict[str, Any]) -> str:
    verification_link = str(context.get("verification_link", "#"))
    return f"Verify your email address here: {verification_link}"
