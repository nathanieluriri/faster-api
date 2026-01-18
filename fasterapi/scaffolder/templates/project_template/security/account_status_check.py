

from fastapi import Depends, HTTPException, Request,status
from schemas.imports import AccountStatus
from schemas.tokens_schema import accessTokenOut
from security.auth import verify_admin_token, verify_token
from services.admin_service import retrieve_admin_by_admin_id
from services.user_service import retrieve_user_by_user_id


async def check_admin_account_status_and_permissions(
    request: Request,
    token: accessTokenOut = Depends(verify_admin_token),
):
    # 1️⃣ Load admin
    admin = await retrieve_admin_by_admin_id(id=token.get("userId"))

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
        )

    # 2️⃣ Check account status
    if admin.accountStatus != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is not active",
        )

    # 3️⃣ Identify current route
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to resolve endpoint",
        )

    endpoint_name = endpoint.__name__
    request_method = request.method.upper()

    # 4️⃣ Ensure permissions exist
    permission_list = getattr(admin, "permissionList", None)

    if not permission_list or not permission_list.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permissions assigned to admin",
        )

    # 5️⃣ Permission check
    for permission in permission_list.permissions:
        if (
            permission.name == endpoint_name
            and request_method in permission.methods
        ):
            # ✅ Authorized
            return admin

    # 6️⃣ Deny if no match
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


async def check_user_account_status_and_permissions(
    request: Request,
    token: accessTokenOut = Depends(verify_token),
):
    user = await retrieve_user_by_user_id(id=token.userId)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.accountStatus != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to resolve endpoint",
        )

    endpoint_name = endpoint.__name__
    request_method = request.method.upper()

    permission_list = getattr(user, "permissionList", None)
    if not permission_list or not permission_list.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permissions assigned to user",
        )

    for permission in permission_list.permissions:
        if (
            permission.name == endpoint_name
            and request_method in permission.methods
        ):
            return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )
    
