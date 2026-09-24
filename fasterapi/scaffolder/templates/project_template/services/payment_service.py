from __future__ import annotations

import asyncio
import logging
import time

from pymongo.errors import DuplicateKeyError

from core.errors import AppException, ErrorCode, resource_not_found
from core.payments import PaymentIntentRequest, PaymentManager
from core.payments.provider import PaymentProvider
from core.payments.types import PaymentStatus, PaymentTransaction
from repositories.payment_repo import (
    claim_webhook_event,
    create_payment_transaction,
    delete_payment_transaction,
    ensure_payment_indexes,
    get_payment_transaction_by_id,
    get_payment_transaction_by_reference,
    release_webhook_event,
    update_payment_transaction,
)
from schemas.payment_schema import PaymentIntentIn, PaymentTransactionCreate, PaymentTransactionOut

logger = logging.getLogger(__name__)


def _epoch() -> int:
    return int(time.time())


def _get_payment_manager() -> PaymentManager:
    try:
        return PaymentManager.get_instance()
    except RuntimeError as err:
        raise AppException(
            status_code=503,
            code=ErrorCode.PAYMENT_PROVIDER_ERROR,
            message="Payment providers are not configured",
            details=str(err),
        ) from err


def _get_provider(name: str | None) -> PaymentProvider:
    try:
        return _get_payment_manager().get_provider((name or "").lower() or None)
    except ValueError as err:
        raise AppException(status_code=400, code=ErrorCode.PAYMENT_PROVIDER_ERROR, message=str(err)) from err


def _conflict(message: str) -> AppException:
    return AppException(status_code=409, code=ErrorCode.PAYMENT_PROVIDER_ERROR, message=message)


async def create_payment_intent(*, owner_id: str, payload: PaymentIntentIn):
    provider = _get_provider(payload.provider)
    await ensure_payment_indexes()

    now = _epoch()
    try:
        # Claim the reference first: the unique index makes a concurrent duplicate fail here.
        await create_payment_transaction(
            PaymentTransactionCreate(
                owner_id=owner_id,
                provider=provider.provider_name,
                reference=payload.reference,
                status=PaymentStatus.PENDING.value,
                amount_minor=payload.amount_minor,
                currency=payload.currency,
                response_payload={},
                idempotency_key=f"{provider.provider_name}:{payload.reference}",
                created_at=now,
                updated_at=now,
            )
        )
    except DuplicateKeyError:
        existing = await get_payment_transaction_by_reference(reference=payload.reference)
        is_retry = (
            existing is not None
            and existing.owner_id == owner_id
            and existing.provider == provider.provider_name
            and existing.amount_minor == payload.amount_minor
            and existing.currency == payload.currency
            and existing.response_payload
        )
        if is_retry:
            return existing
        raise _conflict("This payment reference is already in use")

    try:
        intent = await asyncio.to_thread(
            provider.create_intent,
            PaymentIntentRequest(
                amount_minor=payload.amount_minor,
                currency=payload.currency,
                reference=payload.reference,
                customer_email=payload.customer_email,
                metadata=payload.metadata,
            ),
        )
    except Exception:
        await delete_payment_transaction(reference=payload.reference)
        raise

    return await update_payment_transaction(
        {"reference": payload.reference},
        {"$set": {"status": intent.status.value, "response_payload": intent.provider_payload, "updated_at": _epoch()}},
    )


def _verified_status(tx: PaymentTransactionOut, remote: PaymentTransaction) -> PaymentStatus:
    if remote.status != PaymentStatus.SUCCEEDED:
        return remote.status
    if remote.amount_minor != tx.amount_minor or (remote.currency or "").upper() != tx.currency.upper():
        logger.warning(
            "Payment %s paid %s %s but %s %s was expected; marking it failed",
            tx.reference, remote.amount_minor, remote.currency, tx.amount_minor, tx.currency,
        )
        return PaymentStatus.FAILED
    return PaymentStatus.SUCCEEDED


def _next_status(current: str, incoming: PaymentStatus) -> PaymentStatus:
    # Status only moves forward: a late or retried event can't undo a success or a refund.
    current_status = PaymentStatus(current)
    if current_status == PaymentStatus.REFUNDED:
        return current_status
    if current_status == PaymentStatus.SUCCEEDED and incoming in (PaymentStatus.PENDING, PaymentStatus.FAILED):
        return current_status
    return incoming


async def process_webhook(*, provider_name: str, body: bytes, headers: dict[str, str]):
    provider = _get_provider(provider_name)
    event = provider.verify_webhook(body=body, headers=headers)
    if not event.reference:
        raise AppException(status_code=400, code=ErrorCode.PAYMENT_WEBHOOK_INVALID, message="Webhook missing reference")

    tx = await get_payment_transaction_by_reference(reference=event.reference)
    if tx is None or tx.provider != provider.provider_name:
        raise resource_not_found("PaymentTransaction", event.reference)

    await ensure_payment_indexes()
    if not await claim_webhook_event(provider.provider_name, event.event_id, _epoch()):
        # Already handled; a 2xx stops the provider from retrying.
        return {"processed": False, "duplicate": True, "reference": tx.reference, "status": tx.status}

    try:
        remote = await asyncio.to_thread(
            provider.fetch_transaction, reference=tx.reference, provider_id=tx.response_payload.get("id")
        )
        status = _next_status(tx.status, _verified_status(tx, remote))
        updated = await update_payment_transaction(
            {"reference": tx.reference},
            {"$set": {"status": status.value, "response_payload": remote.raw, "updated_at": _epoch()}},
        )
    except Exception:
        await release_webhook_event(provider.provider_name, event.event_id)
        raise
    return {"processed": True, "reference": tx.reference, "status": updated.status}


async def get_payment_transaction(payment_id: str):
    tx = await get_payment_transaction_by_id(payment_id=payment_id)
    if tx is None:
        raise resource_not_found("PaymentTransaction", payment_id)
    return tx


async def refund_payment(*, payment_id: str, amount_minor: int | None = None):
    tx = await get_payment_transaction_by_id(payment_id=payment_id)
    if tx is None:
        raise resource_not_found("PaymentTransaction", payment_id)
    if tx.status != PaymentStatus.SUCCEEDED.value:
        raise _conflict("Only succeeded payments can be refunded")

    remaining = tx.amount_minor - tx.refunded_minor
    amount = amount_minor or remaining
    if amount > remaining:
        raise AppException(
            status_code=400,
            code=ErrorCode.PAYMENT_PROVIDER_ERROR,
            message="Refund exceeds the amount left to refund",
            details={"remaining_minor": remaining},
        )

    # Reserve the amount atomically so two concurrent refunds can't both pass the check above.
    reserved = await update_payment_transaction(
        {"reference": tx.reference, "status": PaymentStatus.SUCCEEDED.value, "refunded_minor": {"$in": [tx.refunded_minor, None]}},
        {"$inc": {"refunded_minor": amount}},
    )
    if reserved is None:
        raise _conflict("Another refund for this payment is in progress; try again")

    provider = _get_provider(tx.provider)
    try:
        refunded = await asyncio.to_thread(
            provider.refund,
            reference=tx.reference,
            amount_minor=amount,
            currency=tx.currency,
            provider_id=tx.response_payload.get("id"),
        )
    except Exception:
        await update_payment_transaction({"reference": tx.reference}, {"$inc": {"refunded_minor": -amount}})
        raise

    fully_refunded = reserved.refunded_minor >= tx.amount_minor
    return await update_payment_transaction(
        {"reference": tx.reference},
        {
            "$set": {
                "status": (PaymentStatus.REFUNDED if fully_refunded else PaymentStatus.SUCCEEDED).value,
                "last_refund": refunded.raw,
                "updated_at": _epoch(),
            }
        },
    )
