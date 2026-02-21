from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response

from core.errors import auth_permission_denied
from core.response_envelope import document_response
from core.storage.local_provider import LocalStorageProvider
from core.storage.manager import DocumentStorageManager
from schemas.document_schema import CompleteUploadRequest, UploadIntentRequest
from security.auth import verify_any_token
from security.principal import AuthPrincipal
from services.document_service import complete_upload, create_upload_intent, fetch_document, remove_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload-intents")
@document_response(
    message="Upload intent created",
    status_code=201,
    response_codes={400: "Invalid payload", 401: "Unauthorized"},
)
async def create_document_upload_intent(
    payload: UploadIntentRequest,
    principal: AuthPrincipal = Depends(verify_any_token),
):
    intent = await create_upload_intent(owner_id=principal.user_id, payload=payload)
    return {
        "object_key": intent.object_key,
        "upload_url": intent.upload_url,
        "expires_in": intent.expires_in,
        "method": intent.method,
        "headers": intent.headers,
    }


@router.post("/complete")
@document_response(message="Upload completed", status_code=201)
async def complete_document_upload(
    payload: CompleteUploadRequest,
    principal: AuthPrincipal = Depends(verify_any_token),
):
    doc = await complete_upload(owner_id=principal.user_id, payload=payload)
    return doc


@router.get("/{document_id}")
@document_response(message="Document fetched")
async def get_document(document_id: str, principal: AuthPrincipal = Depends(verify_any_token)):
    doc, download_url = await fetch_document(document_id=document_id)
    if doc.owner_id != principal.user_id and not principal.is_admin:
        raise auth_permission_denied("GET:/v1/documents/{document_id}")
    return {"document": doc, "download_url": download_url}


@router.delete("/{document_id}")
@document_response(message="Document deleted")
async def delete_document(document_id: str, principal: AuthPrincipal = Depends(verify_any_token)):
    doc, _download_url = await fetch_document(document_id=document_id)
    if doc.owner_id != principal.user_id and not principal.is_admin:
        raise auth_permission_denied("DELETE:/v1/documents/{document_id}")

    await remove_document(document_id=document_id)
    return {"deleted": True}


@router.post("/upload-local/{object_key}", include_in_schema=False)
async def upload_local_document(object_key: str, file: UploadFile = File(...)):
    if ".." in object_key:
        return Response(status_code=400)
    provider = DocumentStorageManager.get_instance().provider
    if not isinstance(provider, LocalStorageProvider):
        return Response(status_code=404)

    payload = await file.read()
    provider.save_bytes(object_key=object_key, payload=payload)
    return Response(status_code=204)


@router.get("/local/{object_key}", include_in_schema=False)
async def read_local_document(object_key: str):
    if ".." in object_key:
        return Response(status_code=400)
    provider = DocumentStorageManager.get_instance().provider
    if not isinstance(provider, LocalStorageProvider):
        return Response(status_code=404)

    try:
        data = provider.read_bytes(object_key=object_key)
    except FileNotFoundError:
        return Response(status_code=404)
    return Response(content=data)
