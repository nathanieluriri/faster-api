from __future__ import annotations

import json

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
)


class FlutterwavePaymentProvider(PaymentProvider):
    provider_name = PaymentProviderName.FLUTTERWAVE.value

    def __init__(self, *, secret_key: str, webhook_secret_hash: str | None = None) -> None:
        self._secret_key = secret_key
        self._webhook_secret_hash = webhook_secret_hash
        self._base_url = "https://api.flutterwave.com/v3"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._secret_key}",
            "Content-Type": "application/json",
        }

    def create_intent(self, payload: PaymentIntentRequest) -> PaymentIntentResponse:
        response = requests.post(
            f"{self._base_url}/payments",
            json={
                "tx_ref": payload.reference,
                "amount": payload.amount_minor / 100,
                "currency": payload.currency,
                "redirect_url": payload.metadata.get("redirect_url") if payload.metadata else None,
                "customer": {"email": payload.customer_email} if payload.customer_email else None,
                "meta": payload.metadata or {},
            },
            headers=self._headers(),
            timeout=15,
        )
        data = response.json()
        if response.status_code >= 400 or data.get("status") != "success":
            raise AppException(
                status_code=502,
                code=ErrorCode.PAYMENT_PROVIDER_ERROR,
                message="Flutterwave intent creation failed",
                details=data,
            )

        checkout_url = data.get("data", {}).get("link")
        return PaymentIntentResponse(
            provider=PaymentProviderName.FLUTTERWAVE,
            reference=payload.reference,
            status=PaymentStatus.PENDING,
            checkout_url=checkout_url,
            provider_payload=data,
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> WebhookEvent:
        provided = headers.get("verif-hash") or headers.get("Verif-Hash")
        expected = self._webhook_secret_hash
        if expected and provided != expected:
            raise AppException(
                status_code=401,
                code=ErrorCode.PAYMENT_WEBHOOK_INVALID,
                message="Invalid Flutterwave webhook signature",
            )

        payload = json.loads(body.decode("utf-8"))
        event_id = str(payload.get("id") or payload.get("tx_ref") or "unknown")
        event_type = str(payload.get("event") or payload.get("status") or "unknown")
        return WebhookEvent(
            provider=PaymentProviderName.FLUTTERWAVE,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )

    def fetch_transaction(self, *, reference: str) -> PaymentTransaction:
        response = requests.get(
            f"{self._base_url}/transactions/verify_by_reference",
            params={"tx_ref": reference},
            headers=self._headers(),
            timeout=15,
        )
        data = response.json()
        if response.status_code >= 400 or data.get("status") != "success":
            raise AppException(
                status_code=502,
                code=ErrorCode.PAYMENT_PROVIDER_ERROR,
                message="Flutterwave verify failed",
                details=data,
            )

        status = str(data.get("data", {}).get("status", "")).lower()
        mapped = PaymentStatus.SUCCEEDED if status == "successful" else PaymentStatus.PENDING
        return PaymentTransaction(
            provider=PaymentProviderName.FLUTTERWAVE,
            reference=reference,
            status=mapped,
            raw=data,
        )

    def refund(self, *, reference: str, amount_minor: int | None = None) -> PaymentTransaction:
        tx = self.fetch_transaction(reference=reference)
        transaction_id = tx.raw.get("data", {}).get("id")
        if not transaction_id:
            raise AppException(
                status_code=404,
                code=ErrorCode.PAYMENT_PROVIDER_ERROR,
                message="Flutterwave transaction not found for refund",
                details=tx.raw,
            )

        payload = {}
        if amount_minor is not None:
            payload["amount"] = amount_minor / 100

        response = requests.post(
            f"{self._base_url}/transactions/{transaction_id}/refund",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        data = response.json()
        if response.status_code >= 400 or data.get("status") != "success":
            raise AppException(
                status_code=502,
                code=ErrorCode.PAYMENT_PROVIDER_ERROR,
                message="Flutterwave refund failed",
                details=data,
            )

        return PaymentTransaction(
            provider=PaymentProviderName.FLUTTERWAVE,
            reference=reference,
            status=PaymentStatus.REFUNDED,
            raw=data,
        )
