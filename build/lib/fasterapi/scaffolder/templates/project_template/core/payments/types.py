from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PaymentProviderName(str, Enum):
    STRIPE = "stripe"
    FLUTTERWAVE = "flutterwave"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class PaymentIntentRequest:
    amount_minor: int
    currency: str
    reference: str
    customer_email: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class PaymentIntentResponse:
    provider: PaymentProviderName
    reference: str
    status: PaymentStatus
    checkout_url: str | None
    provider_payload: dict[str, Any]


@dataclass(frozen=True)
class WebhookEvent:
    provider: PaymentProviderName
    event_id: str
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class PaymentTransaction:
    provider: PaymentProviderName
    reference: str
    status: PaymentStatus
    raw: dict[str, Any]
