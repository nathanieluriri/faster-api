from __future__ import annotations

import asyncio
import time

from core.errors import AppException, ErrorCode, resource_not_found
from core.storage import DocumentMetadata, DocumentStorageManager
from core.storage.types import MAX_UPLOAD_BYTES
from repositories.document_repo import (
    create_document,
    delete_document,
    get_document_by_id,
    get_document_by_key,
    update_document,
)
from schemas.document_schema import CompleteUploadRequest, DocumentCreate, DocumentOut, UploadIntentRequest


def _epoch() -> int:
    return int(time.time())


def _too_large() -> AppException:
    return AppException(
        status_code=413,
        code=ErrorCode.DOCUMENT_UPLOAD_INVALID,
        message="File too large",
        details={"max_size_bytes": MAX_UPLOAD_BYTES},
    )


async def create_upload_intent(*, owner_id: str, payload: UploadIntentRequest):
    if payload.size > MAX_UPLOAD_BYTES:
        raise _too_large()

    metadata = DocumentMetadata(
        owner_id=owner_id,
        file_name=payload.file_name,
        mime_type=payload.mime_type,
        size=payload.size,
    )
    provider = DocumentStorageManager.get_instance().provider
    intent = provider.create_upload_intent(metadata=metadata)

    # The pending record is what ties the object key to its owner; /complete only accepts keys issued here.
    now = _epoch()
    await create_document(
        DocumentCreate(
            owner_id=owner_id,
            file_name=payload.file_name,
            object_key=intent.object_key,
            backend=provider.backend_name,
            mime_type=payload.mime_type,
            size=payload.size,
            status="pending",
            metadata={"upload_expires_at": now + intent.expires_in},
            created_at=now,
            updated_at=now,
        )
    )
    return intent


async def complete_upload(*, owner_id: str, payload: CompleteUploadRequest) -> DocumentOut:
    doc = await get_document_by_key(object_key=payload.object_key)
    if doc is None or doc.owner_id != owner_id:
        raise resource_not_found("Upload", payload.object_key)
    if doc.status != "pending":
        raise AppException(status_code=409, code=ErrorCode.DOCUMENT_UPLOAD_INVALID, message="Upload already completed")

    provider = DocumentStorageManager.get_instance().provider
    metadata = DocumentMetadata(owner_id=owner_id, file_name=doc.file_name, mime_type=doc.mime_type, size=doc.size)
    try:
        stored = await asyncio.to_thread(
            provider.complete_upload, object_key=doc.object_key, metadata=metadata, checksum=payload.checksum
        )
    except FileNotFoundError:
        raise AppException(
            status_code=400,
            code=ErrorCode.DOCUMENT_UPLOAD_INVALID,
            message="Upload the file to upload_url before completing",
        )

    if stored.size > MAX_UPLOAD_BYTES:
        await asyncio.to_thread(provider.delete_object, object_key=doc.object_key)
        await delete_document(document_id=doc.id)
        raise _too_large()

    return await update_document(
        doc.id,
        {"status": "ready", "size": stored.size, "checksum": stored.checksum, "updated_at": _epoch()},
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
    await asyncio.to_thread(provider.delete_object, object_key=doc.object_key)
    deleted = await delete_document(document_id=document_id)
    if not deleted:
        raise resource_not_found("Document", document_id)
    return True
