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
        """Reject unsigned or malformed events; return the event with its payment reference."""
        ...

    def fetch_transaction(self, *, reference: str, provider_id: str | None = None) -> PaymentTransaction:
        """Look the payment up at the provider, including the amount and currency actually paid."""
        ...

    def refund(
        self, *, reference: str, amount_minor: int, currency: str, provider_id: str | None = None
    ) -> PaymentTransaction:
        ...
