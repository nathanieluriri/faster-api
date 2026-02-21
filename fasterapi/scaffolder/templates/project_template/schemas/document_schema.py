from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from schemas.imports import ObjectId


class UploadIntentRequest(BaseModel):
    file_name: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    size: int = Field(gt=0)


class UploadIntentResponse(BaseModel):
    object_key: str
    upload_url: str
    expires_in: int
    method: str
    headers: dict[str, str] | None = None


class CompleteUploadRequest(BaseModel):
    object_key: str
    file_name: str
    mime_type: str
    size: int = Field(gt=0)
    checksum: str | None = None


class DocumentCreate(BaseModel):
    owner_id: str
    file_name: str
    object_key: str
    backend: str
    mime_type: str
    size: int
    checksum: str | None = None
    status: str = "ready"
    metadata: dict[str, Any] | None = None
    created_at: int
    updated_at: int


class DocumentOut(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    owner_id: str
    file_name: str
    object_key: str
    backend: str
    mime_type: str
    size: int
    checksum: str | None = None
    status: str
    metadata: dict[str, Any] | None = None
    created_at: int
    updated_at: int

    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if isinstance(values, dict) and "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])
        return values

    class Config:
        populate_by_name = True
