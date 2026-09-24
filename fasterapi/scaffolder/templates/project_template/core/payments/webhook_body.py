from __future__ import annotations

import json
from typing import Any

from core.errors import AppException, ErrorCode


def parse_json_object(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        payload = None
    if not isinstance(payload, dict):
        raise AppException(status_code=400, code=ErrorCode.PAYMENT_WEBHOOK_INVALID, message="Webhook body must be a JSON object")
    return payload
