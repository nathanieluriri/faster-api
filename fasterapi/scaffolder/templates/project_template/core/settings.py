from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _redis_url_from_parts() -> str:
    host = os.getenv("REDIS_HOST") or "127.0.0.1"
    port = os.getenv("REDIS_PORT") or "6379"
    password = os.getenv("REDIS_PASSWORD")
    auth = f"{quote(os.getenv('REDIS_USERNAME') or '')}:{quote(password)}@" if password else ""
    return f"redis://{auth}{host}:{port}/0"


@dataclass(frozen=True)
class Settings:
    env: str
    secret_key: str
    session_secret_key: str
    email_host: str | None
    email_port: int
    email_username: str | None
    email_password: str | None
    email_from_email: str | None
    email_sender_name: str
    email_retry_attempts: int
    email_retry_backoff_seconds: float
    email_queue_enabled: bool
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
    scheduler_enabled: bool
    trusted_proxy_hops: int

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env = os.getenv("ENV", "development")
    secret_key = os.getenv("SECRET_KEY", "")
    session_secret_key = os.getenv("SESSION_SECRET_KEY", "")

    default_redis = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or _redis_url_from_parts()

    settings = Settings(
        env=env,
        secret_key=secret_key,
        session_secret_key=session_secret_key,
        email_host=os.getenv("EMAIL_HOST"),
        email_port=int(os.getenv("EMAIL_PORT", "587")),
        email_username=os.getenv("EMAIL_USERNAME"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_from_email=os.getenv("EMAIL_FROM_EMAIL"),
        email_sender_name=os.getenv("EMAIL_SENDER_NAME", "FasterAPI"),
        email_retry_attempts=int(os.getenv("EMAIL_RETRY_ATTEMPTS", "3")),
        email_retry_backoff_seconds=float(os.getenv("EMAIL_RETRY_BACKOFF_SECONDS", "1.0")),
        email_queue_enabled=os.getenv("EMAIL_QUEUE_ENABLED", "true").lower() in {"1", "true", "yes"},
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
        # Serverless platforms like Vercel have no long-running process to keep a scheduler alive.
        scheduler_enabled=(os.getenv("ENABLE_SCHEDULER") or ("false" if os.getenv("VERCEL") else "true")).lower()
        in {"1", "true", "yes"},
        trusted_proxy_hops=int(os.getenv("TRUSTED_PROXY_HOPS") or 1),
    )

    if settings.is_production:
        if not settings.secret_key:
            raise RuntimeError("SECRET_KEY is required when ENV=production")
        if not settings.session_secret_key:
            raise RuntimeError("SESSION_SECRET_KEY is required when ENV=production")
        super_admin_password = os.getenv("SUPER_ADMIN_PASSWORD") or ""
        if super_admin_password and len(super_admin_password) < 12:
            raise RuntimeError("SUPER_ADMIN_PASSWORD must be at least 12 characters when ENV=production")

    return settings
