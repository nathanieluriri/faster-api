from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from schemas.imports import ObjectId


class PaymentIntentIn(BaseModel):
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    reference: str = Field(pattern=r"^[A-Za-z0-9_-]{3,64}$")
    customer_email: str | None = None
    provider: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        return value.upper()


class RefundIn(BaseModel):
    amount_minor: int | None = Field(default=None, gt=0)


class PaymentTransactionCreate(BaseModel):
    owner_id: str
    provider: str
    reference: str
    status: str
    amount_minor: int
    currency: str
    response_payload: dict[str, Any]
    idempotency_key: str
    refunded_minor: int = 0
    created_at: int
    updated_at: int


class PaymentTransactionOut(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    owner_id: str
    provider: str
    reference: str
    status: str
    amount_minor: int
    currency: str
    response_payload: dict[str, Any]
    idempotency_key: str
    refunded_minor: int = 0
    last_refund: dict[str, Any] | None = None
    created_at: int
    updated_at: int

    @model_validator(mode="before")
    @classmethod
    def convert_objectid(cls, values):
        if isinstance(values, dict) and "_id" in values and isinstance(values["_id"], ObjectId):
            values["_id"] = str(values["_id"])
        return values


class WebhookReplayCreate(BaseModel):
    provider: str
    event_id: str
    created_at: int
