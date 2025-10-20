
from bson import ObjectId
from fastapi import HTTPException
from typing import List

from repositories.admin_repo import (
    create_admin,
    get_admin,
    get_admins,
    update_admin,
    delete_admin,
)
from schemas.admin_schema import AdminCreate, AdminUpdate, AdminOut,AdminBase,AdminRefresh
from security.hash import check_password
from repositories.tokens_repo import add_refresh_tokens, add_admin_access_tokens, accessTokenCreate,accessTokenOut,refreshTokenCreate
from repositories.tokens_repo import get_refresh_tokens,get_access_tokens,delete_access_token,delete_refresh_token,delete_all_tokens_with_admin_id
from security.encrypting_jwt import create_jwt_admin_token
async def add_admin(admin_data: AdminCreate) -> AdminOut:
    """adds an entry of AdminCreate to the database and returns an object

    Returns:
        _type_: AdminOut
    """
    admin =  await get_admin(filter_dict={"email":admin_data.email})
    if admin==None:
        new_admin= await create_admin(admin_data)
        access_token = await add_admin_access_tokens(token_data=accessTokenCreate(userId=new_admin.id))
        refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=new_admin.id,previousAccessToken=access_token.accesstoken))
        new_admin.password=""
        new_admin.access_token= await create_jwt_admin_token(token=access_token.accesstoken,userId=new_admin.id)
        new_admin.refresh_token = refresh_token.refreshtoken
        return new_admin
    else:
        raise HTTPException(status_code=409,detail="Admin Already exists")

async def authenticate_admin(admin_data:AdminBase )->AdminOut:
    admin = await get_admin(filter_dict={"email":admin_data.email})

    if admin != None:
        if check_password(password=admin_data.password,hashed=admin.password ):
            admin.password=""
            access_token = await add_admin_access_tokens(token_data=accessTokenCreate(userId=admin.id))
            refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=admin.id,previousAccessToken=access_token.accesstoken))
            admin.access_token=  await create_jwt_admin_token(token=access_token.accesstoken,userId=admin.id)
            admin.refresh_token = refresh_token.refreshtoken
            return admin
        else:
            raise HTTPException(status_code=401, detail="Unathorized, Invalid Login credentials")
    else:
        raise HTTPException(status_code=404,detail="Admin not found")

async def refresh_admin_tokens_reduce_number_of_logins(admin_refresh_data:AdminRefresh,expired_access_token):
    refreshObj= await get_refresh_tokens(admin_refresh_data.refresh_token)
    print("refreshObj","\n",refreshObj,"\n",refreshObj,"expired access token","\n",expired_access_token)
    if refreshObj:
        if refreshObj.previousAccessToken==expired_access_token:
            admin = await get_admin(filter_dict={"_id":ObjectId(refreshObj.userId)})
            
            if admin!= None:
                    access_token = await add_admin_access_tokens(token_data=accessTokenCreate(userId=admin.id))
                    refresh_token  = await add_refresh_tokens(token_data=refreshTokenCreate(userId=admin.id,previousAccessToken=access_token.accesstoken))
                    
                    admin.access_token= await create_jwt_admin_token(token=access_token.accesstoken,userId=refreshObj.userId) 
                    admin.refresh_token = refresh_token.refreshtoken
                    await delete_access_token(accessToken=expired_access_token)
                    await delete_refresh_token(refreshToken=admin_refresh_data.refresh_token)
                    return admin
     
  
    raise HTTPException(status_code=404,detail="Invalid refresh token ")  
        
async def remove_admin(admin_id: str):
    """deletes a field from the database and removes AdminCreateobject 

    Raises:
        HTTPException 400: Invalid admin ID format
        HTTPException 404:  Admin not found
    """
    if not ObjectId.is_valid(admin_id):
        raise HTTPException(status_code=400, detail="Invalid admin ID format")

    filter_dict = {"_id": ObjectId(admin_id)}
    result = await delete_admin(filter_dict)
    await delete_all_tokens_with_admin_id(adminId=admin_id)

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")


async def retrieve_admin_by_admin_id(id: str) -> AdminOut:
    """Retrieves admin object based specific Id 

    Raises:
        HTTPException 404(not found): if  Admin not found in the db
        HTTPException 400(bad request): if  Invalid admin ID format

    Returns:
        _type_: AdminOut
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid admin ID format")

    filter_dict = {"_id": ObjectId(id)}
    result = await get_admin(filter_dict)

    if not result:
        raise HTTPException(status_code=404, detail="Admin not found")

    return result


async def retrieve_admins(start=0,stop=100) -> List[AdminOut]:
    """Retrieves AdminOut Objects in a list

    Returns:
        _type_: AdminOut
    """
    return await get_admins(start=start,stop=stop)


async def update_admin_by_id(admin_id: str, admin_data: AdminUpdate) -> AdminOut:
    """_summary_

    Raises:
        HTTPException 404(not found): if Admin not found or update failed
        HTTPException 400(not found): Invalid admin ID format

    Returns:
        _type_: AdminOut
    """
    if not ObjectId.is_valid(admin_id):
        raise HTTPException(status_code=400, detail="Invalid admin ID format")

    filter_dict = {"_id": ObjectId(admin_id)}
    result = await update_admin(filter_dict, admin_data)

    if not result:
        raise HTTPException(status_code=404, detail="Admin not found or update failed")

    return result

