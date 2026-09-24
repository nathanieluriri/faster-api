from importlib import import_module
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from core.errors import AppException, ErrorCode, resource_not_found
from core.response_envelope import document_response
from schemas.admin_schema import AccountAccessUpdate, AdminBase, AdminCreate, AdminLogin, AdminOut, AdminRefresh
from security.account_status_check import check_admin_account_status_and_permissions
from security.auth import NON_ADMIN_ROLES, verify_admin_refresh_token
from security.permissions import get_router_permissions, ungranted_permissions
from security.principal import AuthPrincipal
from services.admin_service import (
    add_admin,
    authenticate_admin,
    refresh_admin_tokens_reduce_number_of_logins,
    remove_admin,
    retrieve_admins,
    retrieve_role_accounts,
    update_role_account_access,
)

router = APIRouter(prefix="/admins", tags=["Admins"])


@router.get(
    "/",
    dependencies=[
        Depends(check_admin_account_status_and_permissions),
    ],
)
@document_response(message="Admins fetched successfully", success_example=[])
async def list_admins(
    start: Annotated[
        int,
        Query(ge=0, description="The starting index (offset) for the list of admins."),
    ],
    stop: Annotated[
        int,
        Query(gt=0, description="The ending index for the list of admins (limit)."),
    ],
):
    items = await retrieve_admins(start=start, stop=stop)
    return items


@router.get("/profile")
@document_response(message="Admin profile fetched successfully")
async def get_my_admin(admin: AdminOut = Depends(check_admin_account_status_and_permissions)):
    return admin


@router.post("/signup")
@document_response(
    message="Admin created successfully",
    status_code=status.HTTP_201_CREATED,
)
async def signup_new_admin(
    admin_data: AdminBase,
    admin: AdminOut = Depends(check_admin_account_status_and_permissions),
):
    if len(admin_data.password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")
    beyond_inviter = ungranted_permissions(admin_data.permissionList, admin.permissionList)
    if beyond_inviter:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.AUTH_PERMISSION_DENIED,
            message="You can't grant permissions you don't have",
            details={"permissions": beyond_inviter},
        )
    admin_data_dict = admin_data.model_dump()
    new_admin = AdminCreate(invited_by=admin.id, **admin_data_dict) # type: ignore
    items = await add_admin(admin_data=new_admin)
    return items


@router.post("/login")
@document_response(message="Admin login successful")
async def login_admin(admin_data: AdminLogin):
    items = await authenticate_admin(admin_data=admin_data) # type: ignore
    return items


@router.post(
    "/refresh",
)
@document_response(message="Admin tokens refreshed successfully")
async def refresh_admin_tokens(
    admin_data: Annotated[
        AdminRefresh,
        Body(
            openapi_examples={
                "successful_refresh": {
                    "summary": "Successful Token Refresh",
                    "description": (
                        "The correct payload for refreshing tokens. "
                        "The expired access token is provided in the Authorization header."
                    ),
                    "value": {"refresh_token": "valid.long.lived.refresh.token.98765"},
                },
                "invalid_refresh_token": {
                    "summary": "Invalid Refresh Token",
                    "description": (
                        "Payload that fails refresh because the refresh token is invalid or expired."
                    ),
                    "value": {"refresh_token": "expired.or.malformed.refresh.token.00000"},
                },
                "mismatched_tokens": {
                    "summary": "Tokens Belong to Different Admins",
                    "description": (
                        "Refresh token in the body does not match the admin ID from the expired access token."
                    ),
                    "value": {"refresh_token": "refresh.token.of.different.admin.77777"},
                },
            }
        ),
    ],
    principal: AuthPrincipal = Depends(verify_admin_refresh_token),
):
    items = await refresh_admin_tokens_reduce_number_of_logins(
        admin_refresh_data=admin_data,
        expired_access_token=principal.access_token_id,
    )

    items.password = ""
    return items


@router.delete("/account")
@document_response(message="Admin account deleted successfully")
async def delete_admin_account(admin: AdminOut = Depends(check_admin_account_status_and_permissions)):
    result = await remove_admin(admin_id=admin.id) # type: ignore
    return result


def _account_router(role: str):
    if role not in NON_ADMIN_ROLES:
        raise resource_not_found("role", role)
    return import_module(f"api.v1.{role}_route").router


@router.get(
    "/accounts/{role}",
    dependencies=[Depends(check_admin_account_status_and_permissions)],
)
@document_response(message="Accounts fetched successfully", success_example=[])
async def list_accounts(
    role: str,
    start: Annotated[int, Query(ge=0, description="The starting index (offset).")] = 0,
    stop: Annotated[int, Query(gt=0, description="The ending index (limit).")] = 50,
):
    _account_router(role)
    if stop <= start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'stop' must be greater than 'start'")
    return await retrieve_role_accounts(role, start=start, stop=stop)


@router.get(
    "/accounts/{role}/permissions",
    dependencies=[Depends(check_admin_account_status_and_permissions)],
)
@document_response(message="Grantable permissions fetched successfully")
async def list_account_permissions(role: str):
    return get_router_permissions(_account_router(role))


@router.patch(
    "/accounts/{role}/{account_id}",
    dependencies=[Depends(check_admin_account_status_and_permissions)],
)
@document_response(message="Account access updated successfully")
async def update_account_access(role: str, account_id: str, access: AccountAccessUpdate):
    unknown = ungranted_permissions(access.permissionList, get_router_permissions(_account_router(role)))
    if unknown:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_FAILED,
            message=f"These permissions don't match any {role} route",
            details={"permissions": unknown},
        )
    return await update_role_account_access(role, account_id, access)
