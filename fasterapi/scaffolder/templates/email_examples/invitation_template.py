from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "invitation"
SUBJECT = "You were invited to join"


def render_html(context: dict[str, Any]) -> str:
    invitee_name = str(context.get("invitee_name", "there"))
    inviter_name = str(context.get("inviter_name", "A teammate"))
    project_name = str(context.get("project_name", "your workspace"))
    invite_link = str(context.get("invite_link", "#"))
    return (
        "<h2>Project Invitation</h2>"
        f"<p>Hello {invitee_name},</p>"
        f"<p><strong>{inviter_name}</strong> invited you to <strong>{project_name}</strong>.</p>"
        f"<p><a href='{invite_link}'>Accept invitation</a></p>"
    )


def render_text(context: dict[str, Any]) -> str:
    inviter_name = str(context.get("inviter_name", "A teammate"))
    project_name = str(context.get("project_name", "your workspace"))
    invite_link = str(context.get("invite_link", "#"))
    return f"{inviter_name} invited you to {project_name}. Accept here: {invite_link}"
