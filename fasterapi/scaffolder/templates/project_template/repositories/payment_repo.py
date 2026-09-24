from __future__ import annotations

import logging

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from core.database import db
from schemas.payment_schema import PaymentTransactionCreate, PaymentTransactionOut

logger = logging.getLogger(__name__)
_indexes_ready = False


async def ensure_payment_indexes() -> None:
    # Unique indexes make claiming a reference or a webhook event atomic, even across instances.
    global _indexes_ready
    if _indexes_ready:
        return
    try:
        await db.payment_transactions.create_index("reference", unique=True)
        await db.payment_webhook_events.create_index([("provider", 1), ("event_id", 1)], unique=True)
        _indexes_ready = True
    except Exception as exc:
        logger.warning("Could not create payment indexes; duplicate references are not blocked: %s", exc)


async def create_payment_transaction(payload: PaymentTransactionCreate) -> PaymentTransactionOut:
    result = await db.payment_transactions.insert_one(payload.model_dump())
    stored = await db.payment_transactions.find_one({"_id": result.inserted_id})
    return PaymentTransactionOut(**stored)


async def get_payment_transaction_by_reference(reference: str) -> PaymentTransactionOut | None:
    row = await db.payment_transactions.find_one({"reference": reference})
    if row is None:
        return None
    return PaymentTransactionOut(**row)


async def update_payment_transaction(filter_dict: dict, update: dict) -> PaymentTransactionOut | None:
    row = await db.payment_transactions.find_one_and_update(filter_dict, update, return_document=ReturnDocument.AFTER)
    if row is None:
        return None
    return PaymentTransactionOut(**row)


async def delete_payment_transaction(reference: str) -> None:
    await db.payment_transactions.delete_one({"reference": reference})


async def get_payment_transaction_by_id(payment_id: str) -> PaymentTransactionOut | None:
    if not ObjectId.is_valid(payment_id):
        return None
    row = await db.payment_transactions.find_one({"_id": ObjectId(payment_id)})
    if row is None:
        return None
    return PaymentTransactionOut(**row)


async def claim_webhook_event(provider: str, event_id: str, created_at: int) -> bool:
    try:
        await db.payment_webhook_events.insert_one({"provider": provider, "event_id": event_id, "created_at": created_at})
    except DuplicateKeyError:
        return False
    return True


async def release_webhook_event(provider: str, event_id: str) -> None:
    await db.payment_webhook_events.delete_one({"provider": provider, "event_id": event_id})
