from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_ROLE_MISMATCH = "AUTH_ROLE_MISMATCH"
    AUTH_ACCOUNT_INACTIVE = "AUTH_ACCOUNT_INACTIVE"
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"
    AUTH_PRINCIPAL_NOT_FOUND = "AUTH_PRINCIPAL_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    PAYMENT_PROVIDER_ERROR = "PAYMENT_PROVIDER_ERROR"
    PAYMENT_WEBHOOK_INVALID = "PAYMENT_WEBHOOK_INVALID"
    DOCUMENT_UPLOAD_INVALID = "DOCUMENT_UPLOAD_INVALID"


class AppException(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        detail = {
            "message": message,
            "code": code.value,
            "details": details,
        }
        super().__init__(status_code=status_code, detail=detail, headers=headers)


def auth_invalid_token(details: Any | None = None) -> AppException:
    return AppException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=ErrorCode.AUTH_INVALID_TOKEN,
        message="Invalid token",
        details=details,
    )


def auth_role_mismatch(required_role: str, actual_role: str | None) -> AppException:
    return AppException(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.AUTH_ROLE_MISMATCH,
        message="Token role mismatch",
        details={"required_role": required_role, "actual_role": actual_role},
    )


def auth_permission_denied(permission_key: str) -> AppException:
    return AppException(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.AUTH_PERMISSION_DENIED,
        message="Insufficient permissions",
        details={"permission_key": permission_key},
    )


def resource_not_found(resource: str, resource_id: str | None = None) -> AppException:
    details = {"resource": resource}
    if resource_id:
        details["resource_id"] = resource_id
    return AppException(
        status_code=status.HTTP_404_NOT_FOUND,
        code=ErrorCode.RESOURCE_NOT_FOUND,
        message=f"{resource} not found",
        details=details,
    )
