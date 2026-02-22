from __future__ import annotations

from core.email.types import MountedTemplate
from email_templates.starter_template import SUBJECT as starter_subject
from email_templates.starter_template import TEMPLATE_KEY as starter_key
from email_templates.starter_template import render_html as starter_render_html
from email_templates.starter_template import render_text as starter_render_text


def get_mounted_templates() -> list[MountedTemplate]:
    return [
        MountedTemplate(
            key=starter_key,
            subject=starter_subject,
            render_html=starter_render_html,
            render_text=starter_render_text,
        ),
    ]
