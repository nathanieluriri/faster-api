from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "welcome"
SUBJECT = "Welcome to the platform"


def render_html(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    login_link = str(context.get("login_link", "#"))
    return (
        "<h2>Welcome</h2>"
        f"<p>Hello {user_name}, thanks for joining us.</p>"
        f"<p><a href='{login_link}'>Sign in to get started</a></p>"
    )


def render_text(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    login_link = str(context.get("login_link", "#"))
    return f"Hello {user_name}, welcome aboard. Sign in: {login_link}"
