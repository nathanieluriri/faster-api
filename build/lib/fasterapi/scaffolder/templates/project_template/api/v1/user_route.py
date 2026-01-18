
from fastapi import APIRouter, HTTPException, Query, Request, status, Path,Depends
from typing import List

from fastapi.responses import RedirectResponse

from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from schemas.user_schema import (
    UserCreate,
    UserOut,
    UserBase,
    UserUpdate,
    UserRefresh,
    LoginType,
)
from services.user_service import (
    add_user,
    remove_user,
    retrieve_users,
    authenticate_user,
    authenticate_user_google,
    retrieve_user_by_user_id,
    update_user,
    update_user_by_id,
    refresh_user_tokens_reduce_number_of_logins,
    oauth
)
from security.auth import verify_token,verify_token_to_refresh
from security.account_status_check import check_user_account_status_and_permissions
import os
from dotenv import load_dotenv
load_dotenv()



router = APIRouter(prefix="/users", tags=["Users"])

SUCCESS_PAGE_URL = os.getenv("SUCCESS_PAGE_URL", "http://localhost:8080/success")
ERROR_PAGE_URL   = os.getenv("ERROR_PAGE_URL",   "http://localhost:8080/error")

# --- Step 1: Redirect user to Google login ---
@router.get("/google/auth")
async def login_with_google_account(request: Request):
    redirect_uri = request.url_for("auth_callback_user")
    print("REDIRECT URI:", redirect_uri)
 
    return await oauth.google.authorize_redirect(request, redirect_uri)

# --- Step 2: Handle callback from Google ---
@router.get("/auth/callback")
async def auth_callback_user(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')

    # Just print or return user info for now
    if user_info:
        print("✅ Google user info:", user_info)
        rider = UserBase(firstName=user_info['name'],password='',lastName=user_info['given_name'],email=user_info['email'],loginType=LoginType.google)
        data = await authenticate_user_google(user_data=rider)
        access_token = data.access_token
        refresh_token = data.refresh_token

        success_url = f"{SUCCESS_PAGE_URL}?access_token={access_token}&refresh_token={refresh_token}"

        return RedirectResponse(
            url=success_url,
            status_code=status.HTTP_302_FOUND
        )
    else:
        raise HTTPException(status_code=400,detail={"status": "failed", "message": "No user info found"})

@router.get(
    "/",
    response_model_exclude={"data": {"__all__": {"password"}}},
    response_model=APIResponse[List[UserOut]],
    response_model_exclude_none=True,
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def list_users(start:int= 0, stop:int=100):
    items = await retrieve_users(start=0,stop=100)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")

@router.get(
    "/me",
    response_model_exclude={"data": {"password"}},
    response_model=APIResponse[UserOut],
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
    response_model_exclude_none=True,
)
async def get_my_users(token:accessTokenOut = Depends(verify_token)):
    items = await retrieve_user_by_user_id(id=token.userId)
    return APIResponse(status_code=200, data=items, detail="users items fetched")



@router.post("/signup", response_model_exclude={"data": {"password"}},response_model=APIResponse[UserOut])
async def signup_new_user(user_data:UserBase):
    new_user = UserCreate(**user_data.model_dump())
    items = await add_user(user_data=new_user)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.post("/login",response_model_exclude={"data": {"password"}}, response_model=APIResponse[UserOut])
async def login_user(user_data:UserBase):
    items = await authenticate_user(user_data=user_data)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.post("/refresh",response_model_exclude={"data": {"password"}},response_model=APIResponse[UserOut],dependencies=[Depends(verify_token_to_refresh)])
async def refresh_user_tokens(user_data:UserRefresh,token:accessTokenOut = Depends(verify_token_to_refresh)):
    
    items= await refresh_user_tokens_reduce_number_of_logins(user_refresh_data=user_data,expired_access_token=token.accesstoken)

    return APIResponse(status_code=200, data=items, detail="users items fetched")


@router.delete("/account",dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)])
async def delete_user_account(token:accessTokenOut = Depends(verify_token)):
    result = await remove_user(user_id=token.userId)
    return result
