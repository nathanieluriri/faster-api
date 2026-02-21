from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    env: str
    secret_key: str
    session_secret_key: str
    cors_origins: tuple[str, ...]
    debug_include_error_details: bool
    redis_url: str
    s3_bucket_name: str | None
    s3_region: str | None
    s3_endpoint_url: str | None
    storage_backend: str
    storage_local_root: str
    payment_default_provider: str
    stripe_secret_key: str | None
    stripe_webhook_secret: str | None
    flutterwave_secret_key: str | None
    flutterwave_public_key: str | None
    flutterwave_webhook_secret_hash: str | None

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env = os.getenv("ENV", "development")
    secret_key = os.getenv("SECRET_KEY", "")
    session_secret_key = os.getenv("SESSION_SECRET_KEY", "")

    default_redis = (
        os.getenv("CELERY_BROKER_URL")
        or os.getenv("REDIS_URL")
        or f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/0"
    )

    settings = Settings(
        env=env,
        secret_key=secret_key,
        session_secret_key=session_secret_key,
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS")),
        debug_include_error_details=os.getenv("DEBUG_INCLUDE_ERROR_DETAILS", "false").lower()
        in {"1", "true", "yes"},
        redis_url=default_redis,
        s3_bucket_name=os.getenv("S3_BUCKET_NAME"),
        s3_region=os.getenv("S3_REGION"),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        storage_backend=os.getenv("STORAGE_BACKEND", "local").lower(),
        storage_local_root=os.getenv("STORAGE_LOCAL_ROOT", "uploads"),
        payment_default_provider=os.getenv("PAYMENT_DEFAULT_PROVIDER", "flutterwave").lower(),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
        flutterwave_secret_key=os.getenv("FLUTTERWAVE_SECRET_KEY"),
        flutterwave_public_key=os.getenv("FLUTTERWAVE_PUBLIC_KEY"),
        flutterwave_webhook_secret_hash=os.getenv("FLW_WEBHOOK_SECRET_HASH"),
    )

    if settings.is_production:
        if not settings.secret_key:
            raise RuntimeError("SECRET_KEY is required when ENV=production")
        if not settings.session_secret_key:
            raise RuntimeError("SESSION_SECRET_KEY is required when ENV=production")

    return settings
