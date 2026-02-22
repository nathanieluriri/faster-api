from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

TemplateRenderer = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class MountedTemplate:
    key: str
    subject: str
    render_html: TemplateRenderer
    render_text: TemplateRenderer


@dataclass(frozen=True)
class EmailDispatchRequest:
    to_email: str
    template_key: str
    context: Mapping[str, Any] = field(default_factory=dict)
    dispatch: Literal["auto", "sync", "queued"] = "auto"


@dataclass(frozen=True)
class EmailMessage:
    to_email: str
    subject: str
    html_body: str
    text_body: str
    sender_display_name: str


@dataclass(frozen=True)
class EmailSendResult:
    status: Literal["sent", "queued"]
    attempts: int
    task_id: str | None = None
