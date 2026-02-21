from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


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
    created_at: str = datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DocumentMetadata:
    owner_id: str
    file_name: str
    mime_type: str
    size: int
    extra: dict[str, Any] | None = None
