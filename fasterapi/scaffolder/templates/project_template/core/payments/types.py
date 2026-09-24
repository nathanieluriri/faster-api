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


# ISO 4217 currencies without minor units, and those with three decimals.
_ZERO_DECIMAL = {"BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
_THREE_DECIMAL = {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}


def currency_decimals(currency: str) -> int:
    code = currency.upper()
    if code in _ZERO_DECIMAL:
        return 0
    return 3 if code in _THREE_DECIMAL else 2


def to_major_units(amount_minor: int, currency: str) -> int | float:
    decimals = currency_decimals(currency)
    return amount_minor / 10**decimals if decimals else amount_minor


def to_minor_units(amount: float | int | str, currency: str) -> int:
    return int(round(float(amount) * 10 ** currency_decimals(currency)))


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
    reference: str | None = None


@dataclass(frozen=True)
class PaymentTransaction:
    provider: PaymentProviderName
    reference: str
    status: PaymentStatus
    raw: dict[str, Any]
    amount_minor: int | None = None
    currency: str | None = None
