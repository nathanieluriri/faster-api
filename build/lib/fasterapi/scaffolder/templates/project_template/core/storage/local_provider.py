from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from core.storage.provider import DocumentStorageProvider
from core.storage.types import DocumentMetadata, StorageBackend, StoredDocument, UploadIntent


class LocalStorageProvider(DocumentStorageProvider):
    backend_name = StorageBackend.LOCAL.value

    def __init__(self, root_dir: str) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def create_upload_intent(self, metadata: DocumentMetadata) -> UploadIntent:
        extension = Path(metadata.file_name).suffix
        object_key = f"{uuid4().hex}{extension}"
        # Local uploads are completed via API (multipart endpoint)
        return UploadIntent(
            object_key=object_key,
            upload_url=f"/v1/documents/upload-local/{quote(object_key)}",
            expires_in=3600,
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
            size=metadata.size,
            checksum=checksum,
        )

    def download_url(self, *, object_key: str, expires_in: int = 900) -> str:
        return f"/v1/documents/local/{quote(object_key)}"

    def delete_object(self, *, object_key: str) -> None:
        file_path = self._root / object_key
        if file_path.exists():
            file_path.unlink()

    def save_bytes(self, *, object_key: str, payload: bytes) -> int:
        file_path = self._root / object_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(payload)
        return file_path.stat().st_size

    def read_bytes(self, *, object_key: str) -> bytes:
        file_path = self._root / object_key
        return file_path.read_bytes()
