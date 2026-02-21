from __future__ import annotations

from threading import Lock

from core.payments.flutterwave_provider import FlutterwavePaymentProvider
from core.payments.provider import PaymentProvider
from core.payments.stripe_provider import StripePaymentProvider
from core.settings import get_settings


class PaymentManager:
    _instance: "PaymentManager | None" = None
    _lock = Lock()

    def __init__(self, providers: dict[str, PaymentProvider], default_provider: str) -> None:
        self._providers = providers
        self._default_provider = default_provider

    @classmethod
    def configure_from_settings(cls) -> "PaymentManager":
        settings = get_settings()
        providers: dict[str, PaymentProvider] = {}

        if settings.flutterwave_secret_key:
            providers["flutterwave"] = FlutterwavePaymentProvider(
                secret_key=settings.flutterwave_secret_key,
                webhook_secret_hash=settings.flutterwave_webhook_secret_hash,
            )

        if settings.stripe_secret_key:
            providers["stripe"] = StripePaymentProvider(
                secret_key=settings.stripe_secret_key,
                webhook_secret=settings.stripe_webhook_secret,
            )

        if not providers:
            raise RuntimeError(
                "At least one payment provider must be configured. "
                "Set FLUTTERWAVE_SECRET_KEY and/or STRIPE_SECRET_KEY."
            )

        default_provider = settings.payment_default_provider
        if default_provider not in providers:
            default_provider = next(iter(providers.keys()))

        with cls._lock:
            cls._instance = cls(providers=providers, default_provider=default_provider)
            return cls._instance

    @classmethod
    def get_instance(cls) -> "PaymentManager":
        if cls._instance is None:
            return cls.configure_from_settings()
        return cls._instance

    def get_provider(self, provider: str | None = None) -> PaymentProvider:
        key = (provider or self._default_provider).lower()
        if key not in self._providers:
            raise ValueError(f"Unsupported payment provider '{provider}'")
        return self._providers[key]
