from __future__ import annotations

from typing import Protocol

from core.payments.types import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentTransaction,
    WebhookEvent,
)


class PaymentProvider(Protocol):
    provider_name: str

    def create_intent(self, payload: PaymentIntentRequest) -> PaymentIntentResponse:
        ...

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> WebhookEvent:
        ...

    def fetch_transaction(self, *, reference: str) -> PaymentTransaction:
        ...

    def refund(self, *, reference: str, amount_minor: int | None = None) -> PaymentTransaction:
        ...
