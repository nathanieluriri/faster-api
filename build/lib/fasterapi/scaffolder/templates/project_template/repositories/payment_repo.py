from __future__ import annotations

from bson import ObjectId
from pymongo import ReturnDocument

from core.database import db
from schemas.payment_schema import PaymentTransactionCreate, PaymentTransactionOut, WebhookReplayCreate


async def create_payment_transaction(payload: PaymentTransactionCreate) -> PaymentTransactionOut:
    result = await db.payment_transactions.insert_one(payload.model_dump())
    stored = await db.payment_transactions.find_one({"_id": result.inserted_id})
    return PaymentTransactionOut(**stored)


async def get_payment_transaction_by_reference(reference: str) -> PaymentTransactionOut | None:
    row = await db.payment_transactions.find_one({"reference": reference})
    if row is None:
        return None
    return PaymentTransactionOut(**row)


async def update_payment_transaction_status(reference: str, status: str, response_payload: dict) -> PaymentTransactionOut | None:
    row = await db.payment_transactions.find_one_and_update(
        {"reference": reference},
        {"$set": {"status": status, "response_payload": response_payload}},
        return_document=ReturnDocument.AFTER,
    )
    if row is None:
        return None
    return PaymentTransactionOut(**row)


async def get_payment_transaction_by_id(payment_id: str) -> PaymentTransactionOut | None:
    if not ObjectId.is_valid(payment_id):
        return None
    row = await db.payment_transactions.find_one({"_id": ObjectId(payment_id)})
    if row is None:
        return None
    return PaymentTransactionOut(**row)


async def is_webhook_event_processed(provider: str, event_id: str) -> bool:
    row = await db.payment_webhook_events.find_one({"provider": provider, "event_id": event_id})
    return row is not None


async def mark_webhook_event_processed(payload: WebhookReplayCreate) -> None:
    await db.payment_webhook_events.insert_one(payload.model_dump())
