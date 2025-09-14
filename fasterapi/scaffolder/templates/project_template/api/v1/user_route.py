
from fastapi import APIRouter, HTTPException, Query, status, Path,Depends
from typing import List
from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from schemas.user_schema import (
    UserCreate,
    UserOut,
    UserBase,
    UserUpdate,
    UserRefresh,
)
from services.user_service import (
    add_user,
    remove_user,
    retrieve_users,
    authenticate_user,
    retrieve_user_by_user_id,
    update_user,
    refresh_user_tokens_reduce_number_of_logins,

)
from security.auth import verify_token,verify_token_to_refresh
router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{start}/{stop}", response_model=APIResponse[List[UserOut]],response_model_exclude_none=True,dependencies=[Depends(verify_token)])
async def list_users(start:int= 0, stop:int=100):
    items = await retrieve_users(start=0,stop=100)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")

@router.get("/me", response_model=APIResponse[UserOut],dependencies=[Depends(verify_token)],response_model_exclude_none=True)
async def get_my_users(token:accessTokenOut = Depends(verify_token)):
    items = await retrieve_user_by_user_id(id=token.userId)
    return APIResponse(status_code=200, data=items, detail="users items fetched")



@router.post("/signup", response_model=APIResponse[UserOut])
async def signup_new_user(user_data:UserBase):
    new_user = UserCreate(**user_data.model_dump())
    items = await add_user(user_data=new_user)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.post("/login", response_model=APIResponse[UserOut])
async def login_user(user_data:UserBase):
    items = await authenticate_user(user_data=user_data)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.post("/refesh",response_model=APIResponse[UserOut],dependencies=[Depends(verify_token_to_refresh)])
async def refresh_user_tokens(user_data:UserRefresh,token:accessTokenOut = Depends(verify_token_to_refresh)):
    
    items= await refresh_user_tokens_reduce_number_of_logins(user_refresh_data=user_data,expired_access_token=token.accesstoken)

    return APIResponse(status_code=200, data=items, detail="users items fetched")


@router.delete("/account",dependencies=[Depends(verify_token)])
async def delete_user_account(token:accessTokenOut = Depends(verify_token)):
    result = await remove_user(user_id=token.userId)
    return result