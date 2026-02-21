from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.errors import auth_invalid_token, auth_role_mismatch
from repositories.tokens_repo import get_access_token, get_access_token_allow_expired
from security.principal import AuthPrincipal


token_auth_scheme = HTTPBearer(auto_error=True)


async def _resolve_principal(
    credentials: HTTPAuthorizationCredentials,
    *,
    allow_expired: bool,
) -> AuthPrincipal:
    getter = get_access_token_allow_expired if allow_expired else get_access_token
    token_record = await getter(accessToken=credentials.credentials)
    if token_record is None:
        raise auth_invalid_token()

    role = (token_record.role or "").lower()
    if role not in {"member", "admin"}:
        raise auth_invalid_token(details={"role": token_record.role})

    return AuthPrincipal(
        user_id=token_record.userId,
        role=role, # type: ignore
        access_token_id=token_record.accesstoken, # type: ignore
        jwt_token=credentials.credentials,
        allow_expired=allow_expired,
    )


async def verify_any_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await _resolve_principal(credentials, allow_expired=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    principal = await _resolve_principal(credentials, allow_expired=False)
    if principal.role != "member":
        raise auth_role_mismatch(required_role="member", actual_role=principal.role)
    return principal


async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    principal = await _resolve_principal(credentials, allow_expired=False)
    if principal.role != "admin":
        raise auth_role_mismatch(required_role="admin", actual_role=principal.role)
    return principal


async def verify_token_to_refresh(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await _resolve_principal(credentials, allow_expired=True)


async def verify_member_refresh_token(
    principal: AuthPrincipal = Depends(verify_token_to_refresh),
) -> AuthPrincipal:
    if principal.role != "member":
        raise auth_role_mismatch(required_role="member", actual_role=principal.role)
    return principal


async def verify_admin_refresh_token(
    principal: AuthPrincipal = Depends(verify_token_to_refresh),
) -> AuthPrincipal:
    if principal.role != "admin":
        raise auth_role_mismatch(required_role="admin", actual_role=principal.role)
    return principal


# Backward-compatible aliases
async def verify_token_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await verify_token(credentials)


async def verify_admin_token_otp(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
) -> AuthPrincipal:
    return await verify_admin_token(credentials)
