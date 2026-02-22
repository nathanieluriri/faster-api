from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "new_sign_in"
SUBJECT = "New sign-in detected"


def render_html(context: dict[str, Any]) -> str:
    user_name = str(context.get("user_name", "there"))
    sign_in_time = str(context.get("sign_in_time", "unknown time"))
    ip_address = str(context.get("ip_address", "unknown IP"))
    location = str(context.get("location", "unknown location"))
    return (
        "<h2>New Sign-In Alert</h2>"
        f"<p>Hello {user_name},</p>"
        f"<p>We detected a sign-in on <strong>{sign_in_time}</strong>.</p>"
        f"<p>IP: {ip_address}<br/>Location: {location}</p>"
    )


def render_text(context: dict[str, Any]) -> str:
    sign_in_time = str(context.get("sign_in_time", "unknown time"))
    ip_address = str(context.get("ip_address", "unknown IP"))
    location = str(context.get("location", "unknown location"))
    return f"New sign-in detected at {sign_in_time}. IP: {ip_address}. Location: {location}."
