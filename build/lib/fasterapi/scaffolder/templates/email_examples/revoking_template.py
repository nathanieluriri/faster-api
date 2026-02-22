from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "revoked_invitation"
SUBJECT = "Your invitation was revoked"


def render_html(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    project_name = str(context.get("project_name", "this project"))
    revoked_by = str(context.get("revoked_by", "an administrator"))
    return (
        "<h2>Invitation Revoked</h2>"
        f"<p>Hello {user_name},</p>"
        f"<p>Your invitation to <strong>{project_name}</strong> was revoked by {revoked_by}.</p>"
    )


def render_text(context: dict[str, Any]) -> str:
    project_name = str(context.get("project_name", "this project"))
    revoked_by = str(context.get("revoked_by", "an administrator"))
    return f"Your invitation to {project_name} was revoked by {revoked_by}."
