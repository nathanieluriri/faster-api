
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
from repositories.tokens_repo import get_refresh_tokens,delete_access_token,delete_refresh_token,delete_all_tokens_with_user_id
from services.auth_helpers import issue_tokens_for_user
from authlib.integrations.starlette_client import OAuth
import os
from dotenv import load_dotenv


load_dotenv()

 
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)
async def add_user(user_data: UserCreate) -> UserOut:
    """adds an entry of UserCreate to the database and returns an object

    Returns:
        _type_: UserOut
    """
    user =  await get_user(filter_dict={"email":user_data.email})
    if user==None:
        new_user= await create_user(user_data)
        access_token, refresh_token = await issue_tokens_for_user(user_id=new_user.id, role="member") # type: ignore
        new_user.password=""
        new_user.access_token= access_token
        new_user.refresh_token = refresh_token
        return new_user
    else:
        raise HTTPException(status_code=409,detail="User Already exists")

async def authenticate_user(user_data:UserBase )->UserOut:
    user = await get_user(filter_dict={"email":user_data.email})

    if user != None:
        if check_password(password=user_data.password,hashed=user.password ): # type: ignore
            user.password=""
            access_token, refresh_token = await issue_tokens_for_user(user_id=user.id, role="member") # type: ignore
            user.access_token= access_token
            user.refresh_token = refresh_token
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
                    access_token, refresh_token = await issue_tokens_for_user(user_id=user.id, role="member") # type: ignore
                    user.access_token= access_token
                    user.refresh_token = refresh_token
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

async def update_user_by_id(user_id: str, user_data: UserUpdate, is_password_getting_changed: bool = False) -> UserOut:
    """updates an entry of user in the database

    Raises:
        HTTPException 404(not found): if User not found or update failed
        HTTPException 400(not found): Invalid user ID format

    Returns:
        _type_: UserOut
    """
    from core.queue.manager import QueueManager
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    filter_dict = {"_id": ObjectId(user_id)}
    result = await update_user(filter_dict, user_data)
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found or update failed")
    if is_password_getting_changed is True:
        QueueManager.get_instance().enqueue("delete_tokens", {"userId": user_id})
    return result

async def authenticate_user_google(user_data: UserBase) -> UserOut:
    user = await get_user(filter_dict={"email": user_data.email})

    if user is None:
        new_user = await create_user(UserCreate(**user_data.model_dump()))
        user = new_user

    access_token, refresh_token = await issue_tokens_for_user(user_id=user.id, role="member") # type: ignore
    user.password = ""
    user.access_token = access_token
    user.refresh_token = refresh_token
    return user

