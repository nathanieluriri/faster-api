from __future__ import annotations

from importlib import import_module

from fastapi import Depends, HTTPException, status

from core.errors import AppException, ErrorCode
from schemas.imports import AccountStatus
from security.auth import verify_any_token
from security.principal import AuthPrincipal


async def require_active_account(principal: AuthPrincipal = Depends(verify_any_token)) -> AuthPrincipal:
    """Any signed-in account (user, admin or custom role) whose status is still ACTIVE."""
    role = principal.role
    fetch = getattr(import_module(f"services.{role}_service"), f"retrieve_{role}_by_{role}_id")
    try:
        account = await fetch(id=principal.user_id)
    except HTTPException:
        account = None
    if account is None:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_PRINCIPAL_NOT_FOUND,
            message="Account not found",
        )
    if account.accountStatus != AccountStatus.ACTIVE:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AUTH_ACCOUNT_INACTIVE,
            message="Account is not active",
        )
    return principal
