from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
UPLOAD_EXPIRES_IN = 3600

_OBJECT_KEY = re.compile(r"^[0-9a-f]{32}(\.[a-z0-9]{1,16})?$")
_EXTENSION = re.compile(r"^\.[A-Za-z0-9]{1,16}$")


def new_object_key(file_name: str) -> str:
    suffix = Path(file_name).suffix
    return uuid4().hex + (suffix.lower() if _EXTENSION.match(suffix) else "")


def is_valid_object_key(object_key: str) -> bool:
    # Keys are always server-generated, so anything else (paths, "..", absolute names) is rejected.
    return bool(_OBJECT_KEY.match(object_key or ""))


class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3"


@dataclass(frozen=True)
class UploadIntent:
    object_key: str
    upload_url: str
    expires_in: int
    method: str = "PUT"
    headers: dict[str, str] | None = None
    form_fields: dict[str, str] | None = None


@dataclass(frozen=True)
class StoredDocument:
    object_key: str
    backend: StorageBackend
    mime_type: str
    size: int
    checksum: str | None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class DocumentMetadata:
    owner_id: str
    file_name: str
    mime_type: str
    size: int
    extra: dict[str, Any] | None = None
