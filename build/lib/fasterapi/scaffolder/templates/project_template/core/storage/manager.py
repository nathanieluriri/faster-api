from __future__ import annotations

from threading import Lock

from core.settings import get_settings
from core.storage.local_provider import LocalStorageProvider
from core.storage.provider import DocumentStorageProvider
from core.storage.s3_provider import S3StorageProvider


class DocumentStorageManager:
    _instance: "DocumentStorageManager | None" = None
    _lock = Lock()

    def __init__(self, provider: DocumentStorageProvider) -> None:
        self._provider = provider

    @classmethod
    def configure(cls, provider: DocumentStorageProvider) -> "DocumentStorageManager":
        with cls._lock:
            cls._instance = cls(provider)
            return cls._instance

    @classmethod
    def configure_from_settings(cls) -> "DocumentStorageManager":
        settings = get_settings()
        if settings.storage_backend == "s3":
            if not settings.s3_bucket_name:
                raise RuntimeError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3")
            provider: DocumentStorageProvider = S3StorageProvider(
                bucket_name=settings.s3_bucket_name,
                region=settings.s3_region,
                endpoint_url=settings.s3_endpoint_url,
            )
        else:
            provider = LocalStorageProvider(root_dir=settings.storage_local_root)

        return cls.configure(provider)

    @classmethod
    def get_instance(cls) -> "DocumentStorageManager":
        if cls._instance is None:
            return cls.configure_from_settings()
        return cls._instance

    @property
    def provider(self) -> DocumentStorageProvider:
        return self._provider
