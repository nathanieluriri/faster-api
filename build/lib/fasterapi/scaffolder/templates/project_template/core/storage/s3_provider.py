from __future__ import annotations

from uuid import uuid4
from pathlib import Path

from core.storage.provider import DocumentStorageProvider
from core.storage.types import DocumentMetadata, StorageBackend, StoredDocument, UploadIntent


class S3StorageProvider(DocumentStorageProvider):
    backend_name = StorageBackend.S3.value

    def __init__(self, *, bucket_name: str, region: str | None = None, endpoint_url: str | None = None) -> None:
        try:
            import boto3
        except ModuleNotFoundError as err:
            raise RuntimeError("boto3 is required for S3 storage provider") from err

        self._bucket = bucket_name
        self._client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)

    def create_upload_intent(self, metadata: DocumentMetadata) -> UploadIntent:
        extension = Path(metadata.file_name).suffix
        object_key = f"{uuid4().hex}{extension}"
        url = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket, "Key": object_key, "ContentType": metadata.mime_type},
            ExpiresIn=3600,
        )
        return UploadIntent(object_key=object_key, upload_url=url, expires_in=3600, method="PUT")

    def complete_upload(
        self,
        *,
        object_key: str,
        metadata: DocumentMetadata,
        checksum: str | None = None,
    ) -> StoredDocument:
        return StoredDocument(
            object_key=object_key,
            backend=StorageBackend.S3,
            mime_type=metadata.mime_type,
            size=metadata.size,
            checksum=checksum,
        )

    def download_url(self, *, object_key: str, expires_in: int = 900) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )

    def delete_object(self, *, object_key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=object_key)
