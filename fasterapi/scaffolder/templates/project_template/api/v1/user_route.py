from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from core.response_envelope import document_response
from schemas.user_schema import LoginType, UserBase, UserCreate, UserOut, UserRefresh
from services.user_service import (
    add_user,
    authenticate_user,
    authenticate_user_google,
    oauth,
    refresh_user_tokens_reduce_number_of_logins,
    remove_user,
    retrieve_users,
)
from security.account_status_check import check_user_account_status_and_permissions
from security.auth import verify_member_refresh_token
from security.principal import AuthPrincipal
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/users", tags=["Users"])

SUCCESS_PAGE_URL = os.getenv("SUCCESS_PAGE_URL", "http://localhost:8080/success")
ERROR_PAGE_URL = os.getenv("ERROR_PAGE_URL", "http://localhost:8080/error")


@router.get("/google/auth")
async def login_with_google_account(request: Request):
    redirect_uri = request.url_for("auth_callback_user")
    print("REDIRECT URI:", redirect_uri)
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback")
async def auth_callback_user(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if user_info:
        print("✅ Google user info:", user_info)
        rider = UserBase(
            firstName=user_info["name"],
            password="",
            lastName=user_info["given_name"],
            email=user_info["email"],
            loginType=LoginType.google,
        )
        data = await authenticate_user_google(user_data=rider)
        access_token = data.access_token
        refresh_token = data.refresh_token

        success_url = f"{SUCCESS_PAGE_URL}?access_token={access_token}&refresh_token={refresh_token}"

        return RedirectResponse(
            url=success_url,
            status_code=status.HTTP_302_FOUND,
        )

    raise HTTPException(status_code=400, detail={"message": "No user info found"})


@router.get(
    "/",
    dependencies=[Depends(check_user_account_status_and_permissions)],
)
@document_response(
    message="Users fetched successfully",
    success_example=[],
)
async def list_users(start: int = 0, stop: int = 100):
    items = await retrieve_users(start=start, stop=stop)
    return items


@router.get(
    "/me",
)
@document_response(message="User profile fetched successfully")
async def get_my_users(user: UserOut = Depends(check_user_account_status_and_permissions)):
    return user


@router.post("/signup")
@document_response(
    message="User created successfully",
    status_code=status.HTTP_201_CREATED,
)
async def signup_new_user(user_data: UserBase):
    new_user = UserCreate(**user_data.model_dump())
    items = await add_user(user_data=new_user)
    return items


@router.post("/login")
@document_response(message="Login successful")
async def login_user(user_data: UserBase):
    items = await authenticate_user(user_data=user_data)
    return items


@router.post("/refresh")
@document_response(message="Tokens refreshed successfully")
async def refresh_user_tokens(
    user_data: UserRefresh,
    principal: AuthPrincipal = Depends(verify_member_refresh_token),
):
    items = await refresh_user_tokens_reduce_number_of_logins(
        user_refresh_data=user_data,
        expired_access_token=principal.access_token_id,
    )
    return items


@router.delete("/account")
@document_response(message="User account deleted successfully")
async def delete_user_account(user: UserOut = Depends(check_user_account_status_and_permissions)):
    result = await remove_user(user_id=user.id) # type: ignore
    return result
