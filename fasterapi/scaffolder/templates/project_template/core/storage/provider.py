from __future__ import annotations

from typing import Protocol

from core.storage.types import DocumentMetadata, StoredDocument, UploadIntent


class DocumentStorageProvider(Protocol):
    backend_name: str

    def create_upload_intent(self, metadata: DocumentMetadata) -> UploadIntent:
        ...

    def complete_upload(
        self,
        *,
        object_key: str,
        metadata: DocumentMetadata,
        checksum: str | None = None,
    ) -> StoredDocument:
        ...

    def download_url(self, *, object_key: str, expires_in: int = 900) -> str:
        ...

    def delete_object(self, *, object_key: str) -> None:
        ...
