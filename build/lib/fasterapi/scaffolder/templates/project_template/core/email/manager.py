from __future__ import annotations

import asyncio
import logging
from threading import Lock
from typing import Any

from core.email.transport import SMTPTransport, SmtpConfig
from core.email.types import EmailDispatchRequest, EmailMessage, EmailSendResult, MountedTemplate
from core.settings import get_settings


class EmailManager:
    _instance: "EmailManager | None" = None
    _lock = Lock()

    def __init__(
        self,
        *,
        transport: SMTPTransport | None,
        sender_display_name: str,
        retry_attempts: int,
        retry_backoff_seconds: float,
        queue_enabled: bool,
    ) -> None:
        self._transport = transport
        self._sender_display_name = sender_display_name
        self._retry_attempts = max(retry_attempts, 1)
        self._retry_backoff_seconds = max(retry_backoff_seconds, 0.0)
        self._queue_enabled = queue_enabled
        self._templates: dict[str, MountedTemplate] = {}
        self._logger = logging.getLogger(__name__)

    @classmethod
    def configure(cls, manager: "EmailManager") -> "EmailManager":
        with cls._lock:
            cls._instance = manager
            return cls._instance

    @classmethod
    def configure_from_settings(cls) -> "EmailManager":
        settings = get_settings()

        transport: SMTPTransport | None = None
        if settings.email_host and settings.email_username and settings.email_password:
            from_email = settings.email_from_email or settings.email_username
            transport = SMTPTransport(
                SmtpConfig(
                    host=settings.email_host,
                    port=settings.email_port,
                    username=settings.email_username,
                    password=settings.email_password,
                    from_email=from_email,
                )
            )

        manager = cls(
            transport=transport,
            sender_display_name=settings.email_sender_name,
            retry_attempts=settings.email_retry_attempts,
            retry_backoff_seconds=settings.email_retry_backoff_seconds,
            queue_enabled=settings.email_queue_enabled,
        )

        try:
            from core.email.mounted_templates import get_mounted_templates

            for mounted in get_mounted_templates():
                manager.mount_template(mounted)
        except Exception as exc:
            manager._logger.warning("Email templates could not be loaded during startup: %s", exc)

        return cls.configure(manager)

    @classmethod
    def get_instance(cls) -> "EmailManager":
        if cls._instance is None:
            return cls.configure_from_settings()
        return cls._instance

    def mount_template(self, template: MountedTemplate) -> None:
        key = template.key.strip().lower()
        if not key:
            raise ValueError("Template key must not be empty")
        if key in self._templates:
            raise ValueError(f"Template key '{key}' is already mounted")
        self._templates[key] = template

    def list_template_keys(self) -> list[str]:
        return sorted(self._templates.keys())

    async def send_template(self, request: EmailDispatchRequest) -> EmailSendResult:
        mode = request.dispatch
        if mode not in {"auto", "sync", "queued"}:
            raise ValueError(f"Unsupported dispatch mode '{mode}'")

        should_queue = mode == "queued" or (mode == "auto" and self._queue_enabled)
        if should_queue:
            try:
                from core.queue.manager import QueueManager

                queue_result = QueueManager.get_instance().enqueue(
                    "send_email",
                    {
                        "to_email": request.to_email,
                        "template_key": request.template_key,
                        "context": dict(request.context),
                    },
                )
                return EmailSendResult(status="queued", attempts=0, task_id=queue_result.task_id)
            except Exception as exc:
                self._logger.warning("Queue dispatch unavailable. Falling back to sync send: %s", exc)

        subject, html_body, text_body = self._render(request.template_key, request.context)
        return await self.send_message(
            EmailMessage(
                to_email=request.to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                sender_display_name=self._sender_display_name,
            )
        )

    async def send_message(self, message: EmailMessage) -> EmailSendResult:
        if self._transport is None:
            raise RuntimeError(
                "Email transport is not configured. Set EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, and EMAIL_PASSWORD."
            )

        last_error: Exception | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                await asyncio.to_thread(self._transport.send_message, message)
                return EmailSendResult(status="sent", attempts=attempt)
            except Exception as exc:
                last_error = exc
                self._logger.exception(
                    "Email send attempt %s/%s failed for %s",
                    attempt,
                    self._retry_attempts,
                    message.to_email,
                )
                if attempt < self._retry_attempts and self._retry_backoff_seconds > 0:
                    await asyncio.sleep(self._retry_backoff_seconds * attempt)

        raise RuntimeError(
            f"Unable to send email after {self._retry_attempts} attempts"
        ) from last_error

    def _render(self, template_key: str, context: dict[str, Any] | Any) -> tuple[str, str, str]:
        key = template_key.strip().lower()
        template = self._templates.get(key)
        if template is None:
            available = ", ".join(self.list_template_keys()) or "<none>"
            raise ValueError(f"Template '{template_key}' is not mounted. Available: {available}")

        payload = dict(context or {})
        try:
            subject = template.subject.format(**payload)
        except Exception:
            subject = template.subject

        html_body = template.render_html(payload)
        text_body = template.render_text(payload)
        if not isinstance(html_body, str) or not isinstance(text_body, str):
            raise TypeError(f"Template '{template.key}' renderers must return strings")

        return subject, html_body, text_body
