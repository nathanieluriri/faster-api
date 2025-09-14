
from bson import ObjectId
from fastapi import HTTPException
from typing import List

from repositories.user_repo import (
    create_user,
    get_user,
    get_users,
    update_user,
    delete_user,
)
from schemas.user_schema import UserCreate, UserUpdate, UserOut,UserBase,UserRefresh
from security.hash import check_password
from security.encrypting_jwt import create_jwt_member_token
from repositories.tokens_repo import add_refresh_tokens, add_access_tokens, accessTokenCreate,accessTokenOut,refreshTokenCreate
from repositories.tokens_repo import get_refresh_tokens,get_access_tokens,delete_access_token,delete_refresh_token,delete_all_tokens_with_user_id

async def add_user(user_data: UserCreate) -> UserOut:
    """adds an entry of UserCreate to the database and returns an object

    Returns:
        _type_: UserOut
    """
    user =  await get_user(filter_dict={"email":user_data.email})
    if user==None:
        new_user= await create_user(user_data)
        access_token = await add_access_tokens(token_data=accessTokenCreate(userId=new_user.id))
        refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=new_user.id,previousAccessToken=access_token.accesstoken))
        new_user.password=""
        new_user.access_token= access_token.accesstoken 
        new_user.refresh_token = refresh_token.refreshtoken
        return new_user
    else:
        raise HTTPException(status_code=409,detail="User Already exists")

async def authenticate_user(user_data:UserBase )->UserOut:
    user = await get_user(filter_dict={"email":user_data.email})

    if user != None:
        if check_password(password=user_data.password,hashed=user.password ):
            user.password=""
            access_token = await add_access_tokens(token_data=accessTokenCreate(userId=user.id))
            refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=user.id,previousAccessToken=access_token.accesstoken))
            user.access_token= access_token.accesstoken 
            user.refresh_token = refresh_token.refreshtoken
            return user
        else:
            raise HTTPException(status_code=401, detail="Unathorized, Invalid Login credentials")
    else:
        raise HTTPException(status_code=404,detail="User not found")

async def refresh_user_tokens_reduce_number_of_logins(user_refresh_data:UserRefresh,expired_access_token):
    refreshObj= await get_refresh_tokens(user_refresh_data.refresh_token)
    if refreshObj:
        if refreshObj.previousAccessToken==expired_access_token:
            user = await get_user(filter_dict={"_id":ObjectId(refreshObj.userId)})
            
            if user!= None:
                    access_token = await add_access_tokens(token_data=accessTokenCreate(userId=user.id))
                    refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=user.id,previousAccessToken=access_token.accesstoken))
                    user.access_token= access_token.accesstoken 
                    user.refresh_token = refresh_token.refreshtoken
                    await delete_access_token(accessToken=expired_access_token)
                    await delete_refresh_token(refreshToken=user_refresh_data.refresh_token)
                    return user
     
        await delete_refresh_token(refreshToken=user_refresh_data.refresh_token)
        await delete_access_token(accessToken=expired_access_token)
  
    raise HTTPException(status_code=404,detail="Invalid refresh token ")  
        
async def remove_user(user_id: str):
    """deletes a field from the database and removes UserCreateobject 

    Raises:
        HTTPException 400: Invalid user ID format
        HTTPException 404:  User not found
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    filter_dict = {"_id": ObjectId(user_id)}
    result = await delete_user(filter_dict)
    await delete_all_tokens_with_user_id(userId=user_id)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")


async def retrieve_user_by_user_id(id: str) -> UserOut:
    """Retrieves user object based specific Id 

    Raises:
        HTTPException 404(not found): if  User not found in the db
        HTTPException 400(bad request): if  Invalid user ID format

    Returns:
        _type_: UserOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    filter_dict = {"_id": ObjectId(id)}
    result = await get_user(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return result


async def retrieve_users(start=0,stop=100) -> List[UserOut]:
    """Retrieves UserOut Objects in a list

    Returns:
        _type_: UserOut
    """
    return await get_users(start=start,stop=stop)


async def update_user_by_id(user_id: str, user_data: UserUpdate) -> UserOut:
    """_summary_

    Raises:
        HTTPException 404(not found): if User not found or update failed
        HTTPException 400(not found): Invalid user ID format

    Returns:
        _type_: UserOut
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    filter_dict = {"_id": ObjectId(user_id)}
    result = await update_user(filter_dict, user_data)

    if not result:
        raise HTTPException(status_code=404, detail="User not found or update failed")

    return result

