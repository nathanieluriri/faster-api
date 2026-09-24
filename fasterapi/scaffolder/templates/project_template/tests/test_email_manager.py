import asyncio
import smtplib

import pytest

from core.email.manager import EmailManager
from core.email.types import EmailMessage, MountedTemplate


class _FailingTransport:
    def __init__(self, error: Exception) -> None:
        self.error, self.calls = error, 0

    def send_message(self, message: EmailMessage) -> None:
        self.calls += 1
        raise self.error


def _manager(transport=None) -> EmailManager:
    manager = EmailManager(transport=transport, sender_display_name="App", retry_attempts=3, retry_backoff_seconds=0, queue_enabled=False)
    manager.mount_template(
        MountedTemplate(
            key="welcome",
            subject="Welcome {name}",
            render_html=lambda context: f"<p>Hello {context['name']}</p>",
            render_text=lambda context: f"Hello {context['name']}",
        )
    )
    return manager


def test_html_values_are_escaped_and_subject_stays_one_line():
    subject, html_body, text_body = _manager()._render("welcome", {"name": "<script>x</script>\nBcc: a@b.c"})
    assert "<script>" not in html_body and "&lt;script&gt;" in html_body
    assert "\n" not in subject
    assert text_body.startswith("Hello <script>")


def test_permanent_smtp_errors_are_not_retried():
    transport = _FailingTransport(smtplib.SMTPAuthenticationError(535, b"bad credentials"))
    message = EmailMessage(to_email="a@b.c", subject="s", html_body="h", text_body="t", sender_display_name="App")
    with pytest.raises(RuntimeError):
        asyncio.run(_manager(transport).send_message(message))
    assert transport.calls == 1


def test_temporary_smtp_errors_are_retried():
    transport = _FailingTransport(smtplib.SMTPServerDisconnected("dropped"))
    message = EmailMessage(to_email="a@b.c", subject="s", html_body="h", text_body="t", sender_display_name="App")
    with pytest.raises(RuntimeError):
        asyncio.run(_manager(transport).send_message(message))
    assert transport.calls == 3
