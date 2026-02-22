from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from core.email.types import EmailMessage


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    from_email: str


class SMTPTransport:
    def __init__(self, config: SmtpConfig, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)

    def send_message(self, message: EmailMessage) -> None:
        formatted_from = formataddr((message.sender_display_name, self._config.from_email))

        payload = MIMEMultipart("alternative")
        payload["From"] = formatted_from
        payload["To"] = message.to_email
        payload["Subject"] = message.subject
        payload.attach(MIMEText(message.text_body, "plain"))
        payload.attach(MIMEText(message.html_body, "html"))

        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if self._config.port == 465:
                server = smtplib.SMTP_SSL(self._config.host, self._config.port)
            elif self._config.port in (25, 587):
                server = smtplib.SMTP(self._config.host, self._config.port)
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                raise ValueError("Unsupported SMTP port. Use 465, 587, or 25.")

            server.login(self._config.username, self._config.password)
            server.sendmail(self._config.from_email, message.to_email, payload.as_string())
            self._logger.info("Email sent to %s", message.to_email)
        finally:
            if server is not None:
                server.quit()
