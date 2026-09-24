from __future__ import annotations

import hmac
from typing import Any

import requests

from core.errors import AppException, ErrorCode
from core.payments.provider import PaymentProvider
from core.payments.types import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentProviderName,
    PaymentStatus,
    PaymentTransaction,
    WebhookEvent,
    to_major_units,
    to_minor_units,
)
from core.payments.webhook_body import parse_json_object

_STATUSES = {"successful": PaymentStatus.SUCCEEDED, "failed": PaymentStatus.FAILED, "cancelled": PaymentStatus.FAILED}


class FlutterwavePaymentProvider(PaymentProvider):
    provider_name = PaymentProviderName.FLUTTERWAVE.value

    def __init__(self, *, secret_key: str, webhook_secret_hash: str | None = None) -> None:
        self._secret_key = secret_key
        self._webhook_secret_hash = webhook_secret_hash
        self._base_url = "https://api.flutterwave.com/v3"

    def _call(self, method: str, path: str, failure: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {self._secret_key}", "Content-Type": "application/json"},
                timeout=15,
                **kwargs,
            )
            data = response.json()
        except (requests.RequestException, ValueError) as err:
            raise AppException(status_code=502, code=ErrorCode.PAYMENT_PROVIDER_ERROR, message=failure, details=str(err)) from err
        if response.status_code >= 400 or not isinstance(data, dict) or data.get("status") != "success":
            raise AppException(status_code=502, code=ErrorCode.PAYMENT_PROVIDER_ERROR, message=failure, details=data)
        return data

    def create_intent(self, payload: PaymentIntentRequest) -> PaymentIntentResponse:
        data = self._call(
            "POST",
            "/payments",
            "Flutterwave intent creation failed",
            json={
                "tx_ref": payload.reference,
                "amount": to_major_units(payload.amount_minor, payload.currency),
                "currency": payload.currency,
                "redirect_url": payload.metadata.get("redirect_url") if payload.metadata else None,
                "customer": {"email": payload.customer_email} if payload.customer_email else None,
                "meta": payload.metadata or {},
            },
        )
        return PaymentIntentResponse(
            provider=PaymentProviderName.FLUTTERWAVE,
            reference=payload.reference,
            status=PaymentStatus.PENDING,
            checkout_url=data.get("data", {}).get("link"),
            provider_payload=data,
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> WebhookEvent:
        expected = self._webhook_secret_hash
        provided = headers.get("verif-hash") or ""
        if not expected or not hmac.compare_digest(provided.encode(), expected.encode()):
            raise AppException(
                status_code=401,
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                message="Invalid Flutterwave webhook signature"
                if expected
                else "FLW_WEBHOOK_SECRET_HASH is not configured, so webhooks can't be verified",
            )

        payload = parse_json_object(body)
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        event_type = str(payload.get("event") or "")
        if not data.get("id") or not event_type:
            raise AppException(status_code=400, code=ErrorCode.PAYMENT_WEBHOOK_INVALID, message="Webhook missing event or transaction id")
        return WebhookEvent(
            provider=PaymentProviderName.FLUTTERWAVE,
            event_id=f"{event_type}:{data['id']}",
            event_type=event_type,
            payload=payload,
            reference=data.get("tx_ref"),
        )

    def fetch_transaction(self, *, reference: str, provider_id: str | None = None) -> PaymentTransaction:
        data = self._call(
            "GET", "/transactions/verify_by_reference", "Flutterwave verify failed", params={"tx_ref": reference}
        )
        transaction = data.get("data") or {}
        currency = str(transaction.get("currency") or "").upper()
        amount = transaction.get("amount")
        return PaymentTransaction(
            provider=PaymentProviderName.FLUTTERWAVE,
            reference=reference,
            status=_STATUSES.get(str(transaction.get("status", "")).lower(), PaymentStatus.PENDING),
            raw=data,
            amount_minor=to_minor_units(amount, currency) if amount is not None and currency else None,
            currency=currency or None,
        )

    def refund(
        self, *, reference: str, amount_minor: int, currency: str, provider_id: str | None = None
    ) -> PaymentTransaction:
        transaction_id = (self.fetch_transaction(reference=reference).raw.get("data") or {}).get("id")
        if not transaction_id:
            raise AppException(
                status_code=404,
                code=ErrorCode.PAYMENT_PROVIDER_ERROR,
                message="Flutterwave transaction not found for refund",
            )
        data = self._call(
            "POST",
            f"/transactions/{transaction_id}/refund",
            "Flutterwave refund failed",
            json={"amount": to_major_units(amount_minor, currency)},
        )
        return PaymentTransaction(
            provider=PaymentProviderName.FLUTTERWAVE,
            reference=reference,
            status=PaymentStatus.REFUNDED,
            raw=data,
        )
