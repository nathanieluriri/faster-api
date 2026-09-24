from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import AsyncIterator

from core.storage.provider import DocumentStorageProvider
from core.storage.types import (
    UPLOAD_EXPIRES_IN,
    DocumentMetadata,
    StorageBackend,
    StoredDocument,
    UploadIntent,
    is_valid_object_key,
    new_object_key,
)


class UploadTooLarge(Exception):
    pass


class LocalStorageProvider(DocumentStorageProvider):
    """Stores files on local disk and hands out expiring signed URLs, like S3 presigned URLs."""

    backend_name = StorageBackend.LOCAL.value

    def __init__(self, root_dir: str, signing_key: str) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._signing_key = signing_key.encode()

    def _path(self, object_key: str) -> Path:
        if not is_valid_object_key(object_key):
            raise ValueError("Invalid object key")
        return self._root / object_key

    def _signature(self, action: str, object_key: str, expires: int) -> str:
        message = f"{action}:{object_key}:{expires}".encode()
        return hmac.new(self._signing_key, message, hashlib.sha256).hexdigest()

    def _signed_url(self, path: str, action: str, object_key: str, expires_in: int) -> str:
        expires = int(time.time()) + expires_in
        return f"{path}/{object_key}?expires={expires}&signature={self._signature(action, object_key, expires)}"

    def verify_signature(self, *, action: str, object_key: str, expires: int, signature: str) -> bool:
        if not is_valid_object_key(object_key) or expires < time.time():
            return False
        return hmac.compare_digest(signature, self._signature(action, object_key, expires))

    def create_upload_intent(self, metadata: DocumentMetadata) -> UploadIntent:
        object_key = new_object_key(metadata.file_name)
        return UploadIntent(
            object_key=object_key,
            upload_url=self._signed_url("/v1/documents/upload-local", "upload", object_key, UPLOAD_EXPIRES_IN),
            expires_in=UPLOAD_EXPIRES_IN,
            method="POST",
        )

    def complete_upload(
        self,
        *,
        object_key: str,
        metadata: DocumentMetadata,
        checksum: str | None = None,
    ) -> StoredDocument:
        return StoredDocument(
            object_key=object_key,
            backend=StorageBackend.LOCAL,
            mime_type=metadata.mime_type,
            size=self._path(object_key).stat().st_size,
            checksum=checksum,
        )

    def download_url(self, *, object_key: str, expires_in: int = 900) -> str:
        return self._signed_url("/v1/documents/local", "download", object_key, expires_in)

    def delete_object(self, *, object_key: str) -> None:
        self._path(object_key).unlink(missing_ok=True)

    async def save_stream(self, *, object_key: str, chunks: AsyncIterator[bytes], max_bytes: int) -> int:
        target = self._path(object_key)
        partial = target.with_name(target.name + ".part")
        written = 0
        try:
            with partial.open("wb") as handle:
                async for chunk in chunks:
                    written += len(chunk)
                    if written > max_bytes:
                        raise UploadTooLarge()
                    handle.write(chunk)
            os.replace(partial, target)
        finally:
            partial.unlink(missing_ok=True)
        return written

    def read_bytes(self, *, object_key: str) -> bytes:
        return self._path(object_key).read_bytes()
