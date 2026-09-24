from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from core.errors import auth_permission_denied
from core.response_envelope import document_response
from core.storage.local_provider import LocalStorageProvider, UploadTooLarge
from core.storage.manager import DocumentStorageManager
from core.storage.types import MAX_UPLOAD_BYTES
from repositories.document_repo import get_document_by_key
from schemas.document_schema import CompleteUploadRequest, UploadIntentRequest
from security.active_account import require_active_account
from security.principal import AuthPrincipal
from services.document_service import complete_upload, create_upload_intent, fetch_document, remove_document

router = APIRouter(prefix="/documents", tags=["Documents"])

# Types a browser could run as a page on the API's origin are always served as downloads.
_ALWAYS_DOWNLOAD = {"text/html", "application/xhtml+xml", "image/svg+xml", "text/xml", "application/xml"}


def _local_provider() -> LocalStorageProvider | None:
    provider = DocumentStorageManager.get_instance().provider
    return provider if isinstance(provider, LocalStorageProvider) else None


@router.post("/upload-intents")
@document_response(
    message="Upload intent created",
    status_code=201,
    response_codes={400: "Invalid payload", 401: "Unauthorized", 413: "File too large"},
)
async def create_document_upload_intent(
    payload: UploadIntentRequest,
    principal: AuthPrincipal = Depends(require_active_account),
):
    intent = await create_upload_intent(owner_id=principal.user_id, payload=payload)
    return {
        "object_key": intent.object_key,
        "upload_url": intent.upload_url,
        "expires_in": intent.expires_in,
        "method": intent.method,
        "headers": intent.headers,
        "form_fields": intent.form_fields,
    }


@router.post("/complete")
@document_response(message="Upload completed", status_code=201)
async def complete_document_upload(
    payload: CompleteUploadRequest,
    principal: AuthPrincipal = Depends(require_active_account),
):
    doc = await complete_upload(owner_id=principal.user_id, payload=payload)
    return doc


@router.get("/{document_id}")
@document_response(message="Document fetched")
async def get_document(document_id: str, principal: AuthPrincipal = Depends(require_active_account)):
    doc, download_url = await fetch_document(document_id=document_id)
    if doc.owner_id != principal.user_id and not principal.is_admin:
        raise auth_permission_denied("GET:/v1/documents/{document_id}")
    return {"document": doc, "download_url": download_url}


@router.delete("/{document_id}")
@document_response(message="Document deleted")
async def delete_document(document_id: str, principal: AuthPrincipal = Depends(require_active_account)):
    doc, _download_url = await fetch_document(document_id=document_id)
    if doc.owner_id != principal.user_id and not principal.is_admin:
        raise auth_permission_denied("DELETE:/v1/documents/{document_id}")

    await remove_document(document_id=document_id)
    return {"deleted": True}


@router.post("/upload-local/{object_key}", include_in_schema=False)
async def upload_local_document(
    object_key: str,
    request: Request,
    expires: int = Query(...),
    signature: str = Query(...),
):
    provider = _local_provider()
    if provider is None:
        return Response(status_code=404)
    if not provider.verify_signature(action="upload", object_key=object_key, expires=expires, signature=signature):
        return Response(status_code=403)

    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES + 64 * 1024:
        return Response(status_code=413)

    form = await request.form(max_files=1, max_fields=0)
    upload = form.get("file")
    if upload is None or isinstance(upload, str):
        return Response(status_code=400)

    async def chunks():
        while chunk := await upload.read(1024 * 1024):
            yield chunk

    try:
        await provider.save_stream(object_key=object_key, chunks=chunks(), max_bytes=MAX_UPLOAD_BYTES)
    except UploadTooLarge:
        return Response(status_code=413)
    return Response(status_code=204)


@router.get("/local/{object_key}", include_in_schema=False)
async def read_local_document(
    object_key: str,
    expires: int = Query(...),
    signature: str = Query(...),
):
    provider = _local_provider()
    if provider is None:
        return Response(status_code=404)
    if not provider.verify_signature(action="download", object_key=object_key, expires=expires, signature=signature):
        return Response(status_code=403)

    doc = await get_document_by_key(object_key=object_key)
    try:
        data = provider.read_bytes(object_key=object_key)
    except FileNotFoundError:
        return Response(status_code=404)

    media_type = doc.mime_type if doc else "application/octet-stream"
    disposition = "attachment" if media_type.split(";")[0].strip().lower() in _ALWAYS_DOWNLOAD else "inline"
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": disposition,
            "Content-Security-Policy": "sandbox",
        },
    )
