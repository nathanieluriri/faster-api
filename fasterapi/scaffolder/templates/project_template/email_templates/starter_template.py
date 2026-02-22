from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "starter"
SUBJECT = "Starter Email Template"


def render_html(context: dict[str, Any]) -> str:
    recipient_name = str(context.get("recipient_name", "there"))
    action_link = str(context.get("action_link", "#"))
    return (
        "<h2>Starter Template</h2>"
        f"<p>Hello {recipient_name}, this is your starter email template.</p>"
        f"<p><a href='{action_link}'>Continue</a></p>"
    )


def render_text(context: dict[str, Any]) -> str:
    recipient_name = str(context.get("recipient_name", "there"))
    action_link = str(context.get("action_link", "#"))
    return f"Hello {recipient_name}, this is your starter email template. Continue: {action_link}"
