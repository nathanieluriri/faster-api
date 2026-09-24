from __future__ import annotations

from core.storage.provider import DocumentStorageProvider
from core.storage.types import (
    MAX_UPLOAD_BYTES,
    UPLOAD_EXPIRES_IN,
    DocumentMetadata,
    StorageBackend,
    StoredDocument,
    UploadIntent,
    new_object_key,
)


class S3StorageProvider(DocumentStorageProvider):
    backend_name = StorageBackend.S3.value

    def __init__(self, *, bucket_name: str, region: str | None = None, endpoint_url: str | None = None) -> None:
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ModuleNotFoundError as err:
            raise RuntimeError("boto3 is required for S3 storage provider") from err

        self._bucket = bucket_name
        self._client = boto3.client("s3", region_name=region or None, endpoint_url=endpoint_url or None)
        self._client_error = ClientError

    def create_upload_intent(self, metadata: DocumentMetadata) -> UploadIntent:
        object_key = new_object_key(metadata.file_name)
        # A presigned POST (unlike a presigned PUT) lets S3 enforce the size limit and content type.
        post = self._client.generate_presigned_post(
            Bucket=self._bucket,
            Key=object_key,
            Fields={"Content-Type": metadata.mime_type},
            Conditions=[{"Content-Type": metadata.mime_type}, ["content-length-range", 1, MAX_UPLOAD_BYTES]],
            ExpiresIn=UPLOAD_EXPIRES_IN,
        )
        return UploadIntent(
            object_key=object_key,
            upload_url=post["url"],
            expires_in=UPLOAD_EXPIRES_IN,
            method="POST",
            form_fields=post["fields"],
        )

    def complete_upload(
        self,
        *,
        object_key: str,
        metadata: DocumentMetadata,
        checksum: str | None = None,
    ) -> StoredDocument:
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=object_key)
        except self._client_error as err:
            raise FileNotFoundError(object_key) from err
        return StoredDocument(
            object_key=object_key,
            backend=StorageBackend.S3,
            mime_type=head.get("ContentType") or metadata.mime_type,
            size=int(head["ContentLength"]),
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
