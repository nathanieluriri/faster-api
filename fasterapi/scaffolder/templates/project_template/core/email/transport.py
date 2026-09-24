from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from core.email.types import EmailMessage


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    from_email: str
    # "ssl" (implicit TLS, port 465), "starttls" (587, 2525, 25) or "none" (local catchers like Mailpit)
    security: str = "starttls"
    timeout_seconds: float = 15.0


def default_security(port: int) -> str:
    return {465: "ssl", 1025: "none"}.get(port, "starttls")


class SMTPTransport:
    def __init__(self, config: SmtpConfig, logger: logging.Logger | None = None) -> None:
        if config.security not in {"ssl", "starttls", "none"}:
            raise ValueError("EMAIL_SECURITY must be ssl, starttls or none")
        self._config = config
        self._logger = logger or logging.getLogger(__name__)

    def _connect(self) -> smtplib.SMTP:
        config = self._config
        # A verifying context: without it smtplib accepts any certificate, exposing the SMTP password.
        context = ssl.create_default_context()
        if config.security == "ssl":
            return smtplib.SMTP_SSL(config.host, config.port, timeout=config.timeout_seconds, context=context)
        server = smtplib.SMTP(config.host, config.port, timeout=config.timeout_seconds)
        if config.security == "starttls":
            server.starttls(context=context)
        return server

    def send_message(self, message: EmailMessage) -> None:
        payload = MIMEMultipart("alternative")
        payload["From"] = formataddr((message.sender_display_name, self._config.from_email))
        payload["To"] = message.to_email
        payload["Subject"] = message.subject
        # utf-8 bodies are base64 encoded, which also keeps lines under SMTP's 998 character limit.
        payload.attach(MIMEText(message.text_body, "plain", "utf-8"))
        payload.attach(MIMEText(message.html_body, "html", "utf-8"))

        server = self._connect()
        try:
            if self._config.username and self._config.password:
                server.login(self._config.username, self._config.password)
            server.sendmail(self._config.from_email, [message.to_email], payload.as_string())
            self._logger.info("Email sent to %s", message.to_email)
        finally:
            # A failed QUIT after the message was accepted must not look like a failed send (and trigger a resend).
            try:
                server.quit()
            except (smtplib.SMTPException, OSError):
                server.close()
