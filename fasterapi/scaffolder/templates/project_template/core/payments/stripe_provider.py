from __future__ import annotations

from typing import Any

from core.errors import AppException, ErrorCode
from core.payments.provider import PaymentProvider
from core.payments.types import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentProviderName,
    PaymentStatus,
    PaymentTransaction,
    WebhookEvent,
)

_STATUSES = {"succeeded": PaymentStatus.SUCCEEDED, "canceled": PaymentStatus.FAILED}


def _plain(obj: Any) -> dict[str, Any]:
    # Stripe objects stopped being dict subclasses; to_dict() converts nested objects too.
    for method in ("to_dict", "to_dict_recursive"):
        convert = getattr(obj, method, None)
        if callable(convert):
            return convert()
    return dict(obj)


class StripePaymentProvider(PaymentProvider):
    provider_name = PaymentProviderName.STRIPE.value

    def __init__(self, *, secret_key: str, webhook_secret: str | None = None) -> None:
        try:
            import stripe
        except ModuleNotFoundError as err:
            raise RuntimeError("stripe package is required for StripePaymentProvider") from err

        self._stripe = stripe
        self._stripe.api_key = secret_key
        self._webhook_secret = webhook_secret

    def _fail(self, message: str, err: Exception) -> AppException:
        return AppException(status_code=502, code=ErrorCode.PAYMENT_PROVIDER_ERROR, message=message, details=str(err))

    def create_intent(self, payload: PaymentIntentRequest) -> PaymentIntentResponse:
        try:
            intent = self._stripe.PaymentIntent.create(
                amount=payload.amount_minor,
                currency=payload.currency.lower(),
                # The reference goes last so client metadata can't replace it.
                metadata={**(payload.metadata or {}), "reference": payload.reference},
                receipt_email=payload.customer_email,
                automatic_payment_methods={"enabled": True},
            )
        except Exception as err:
            raise self._fail("Stripe intent creation failed", err) from err

        return PaymentIntentResponse(
            provider=PaymentProviderName.STRIPE,
            reference=payload.reference,
            status=PaymentStatus.PENDING,
            checkout_url=None,
            provider_payload={"client_secret": intent.client_secret, "id": intent.id},
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> WebhookEvent:
        signature = headers.get("stripe-signature")
        if not signature or not self._webhook_secret:
            raise AppException(
                status_code=401,
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                message="Missing Stripe webhook signature",
            )

        try:
            event = self._stripe.Webhook.construct_event(payload=body, sig_header=signature, secret=self._webhook_secret)
        except ValueError as err:
            raise AppException(status_code=400, code=ErrorCode.PAYMENT_WEBHOOK_INVALID, message="Invalid Stripe webhook body") from err
        except Exception as err:
            raise AppException(
                status_code=401,
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                message="Invalid Stripe webhook signature",
                details=str(err),
            ) from err

        payload = _plain(event)
        obj = (payload.get("data") or {}).get("object") or {}
        return WebhookEvent(
            provider=PaymentProviderName.STRIPE,
            event_id=payload["id"],
            event_type=payload["type"],
            payload=payload,
            reference=(obj.get("metadata") or {}).get("reference"),
        )

    def fetch_transaction(self, *, reference: str, provider_id: str | None = None) -> PaymentTransaction:
        try:
            if provider_id:
                intent = self._stripe.PaymentIntent.retrieve(provider_id)
            else:
                # References are limited to letters, digits, "-" and "_", so they can't break out of the query.
                found = self._stripe.PaymentIntent.search(query=f"metadata['reference']:'{reference}'", limit=1)
                intent = found.data[0] if found.data else None
        except Exception as err:
            raise self._fail("Stripe lookup failed", err) from err
        if intent is None:
            raise AppException(
                status_code=404,
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Stripe transaction not found",
                details={"reference": reference},
            )

        raw = _plain(intent)
        return PaymentTransaction(
            provider=PaymentProviderName.STRIPE,
            reference=reference,
            status=_STATUSES.get(raw.get("status"), PaymentStatus.PENDING),
            raw=raw,
            amount_minor=raw.get("amount_received") or raw.get("amount"),
            currency=str(raw.get("currency") or "").upper() or None,
        )

    def refund(
        self, *, reference: str, amount_minor: int, currency: str, provider_id: str | None = None
    ) -> PaymentTransaction:
        intent_id = provider_id or self.fetch_transaction(reference=reference).raw.get("id")
        try:
            refund = self._stripe.Refund.create(payment_intent=intent_id, amount=amount_minor)
        except Exception as err:
            raise self._fail("Stripe refund failed", err) from err
        return PaymentTransaction(
            provider=PaymentProviderName.STRIPE,
            reference=reference,
            status=PaymentStatus.REFUNDED,
            raw=_plain(refund),
        )
