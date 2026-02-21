from __future__ import annotations

import time

from core.errors import AppException, ErrorCode, resource_not_found
from core.storage import DocumentMetadata, DocumentStorageManager
from repositories.document_repo import create_document, delete_document, get_document_by_id
from schemas.document_schema import CompleteUploadRequest, DocumentCreate, DocumentOut, UploadIntentRequest


def _epoch() -> int:
    return int(time.time())


async def create_upload_intent(*, owner_id: str, payload: UploadIntentRequest):
    metadata = DocumentMetadata(
        owner_id=owner_id,
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        size=payload.size,
    )
    provider = DocumentStorageManager.get_instance().provider
    return provider.create_upload_intent(metadata=metadata)


async def complete_upload(*, owner_id: str, payload: CompleteUploadRequest) -> DocumentOut:
    if payload.size > 50 * 1024 * 1024:
        raise AppException(
            status_code=413,
            code=ErrorCode.DOCUMENT_UPLOAD_INVALID,
            message="File too large",
            details={"max_size_bytes": 50 * 1024 * 1024},
        )

    metadata = DocumentMetadata(
        owner_id=owner_id,
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        size=payload.size,
    )
    provider = DocumentStorageManager.get_instance().provider
    stored = provider.complete_upload(
        object_key=payload.object_key,
        metadata=metadata,
        checksum=payload.checksum,
    )

    return await create_document(
        DocumentCreate(
            owner_id=owner_id,
            file_name=payload.file_name,
            object_key=stored.object_key,
            backend=stored.backend.value,
            mime_type=stored.mime_type,
            size=stored.size,
            checksum=stored.checksum,
            metadata=payload.model_dump(),
            created_at=_epoch(),
            updated_at=_epoch(),
        )
    )


async def fetch_document(document_id: str) -> tuple[DocumentOut, str]:
    doc = await get_document_by_id(document_id=document_id)
    if doc is None:
        raise resource_not_found("Document", document_id)

    provider = DocumentStorageManager.get_instance().provider
    return doc, provider.download_url(object_key=doc.object_key)


async def remove_document(document_id: str) -> bool:
    doc = await get_document_by_id(document_id=document_id)
    if doc is None:
        raise resource_not_found("Document", document_id)

    provider = DocumentStorageManager.get_instance().provider
    provider.delete_object(object_key=doc.object_key)
    deleted = await delete_document(document_id=document_id)
    if not deleted:
        raise resource_not_found("Document", document_id)
    return True
