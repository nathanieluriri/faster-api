from __future__ import annotations

from typing import Any

TEMPLATE_KEY = "otp"
SUBJECT = "Your one-time passcode"


def render_html(context: dict[str, Any]) -> str:
    otp_code = str(context.get("otp_code", "000000"))
    expires_in = str(context.get("expires_in", "10 minutes"))
    return (
        "<h2>One-Time Passcode</h2>"
        f"<p>Your OTP is <strong>{otp_code}</strong>.</p>"
        f"<p>This code expires in {expires_in}.</p>"
    )


def render_text(context: dict[str, Any]) -> str:
    otp_code = str(context.get("otp_code", "000000"))
    expires_in = str(context.get("expires_in", "10 minutes"))
    return f"Your OTP is {otp_code}. It expires in {expires_in}."
