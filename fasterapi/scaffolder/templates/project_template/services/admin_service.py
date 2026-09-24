
import time

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from typing import List

from core.database import db

from repositories.admin_repo import (
    create_admin,
    get_admin,
    get_admins,
    update_admin,
    delete_admin,
)
from schemas.admin_schema import AccountAccessUpdate, AdminCreate, AdminUpdate, AdminOut,AdminBase,AdminRefresh
from schemas.imports import AccountStatus, PermissionList
from security.hash import check_password
from security.permissions import get_endpoint_permissions
from repositories.tokens_repo import get_refresh_tokens,delete_access_token,delete_refresh_token,delete_all_tokens_with_admin_id,delete_access_and_refresh_token_with_user_id
from services.auth_helpers import issue_tokens_for_user

# What every invited admin may do on their own account, on top of what the inviter grants.
DEFAULT_ADMIN_ENDPOINTS = {"get_my_admin", "delete_admin_account"}


def _with_default_access(admin_data: AdminCreate) -> AdminCreate:
    from api.v1.admin_route import router  # imported here because the route module imports this service

    granted = admin_data.permissionList.permissions if admin_data.permissionList else []
    granted_keys = {permission.key for permission in granted}
    defaults = get_endpoint_permissions(router, DEFAULT_ADMIN_ENDPOINTS).permissions
    admin_data.permissionList = PermissionList(
        permissions=[*granted, *(permission for permission in defaults if permission.key not in granted_keys)]
    )
    return admin_data


async def add_admin(admin_data: AdminCreate) -> AdminOut:
    """adds an entry of AdminCreate to the database and returns an object

    Returns:
        _type_: AdminOut
    """
    admin =  await get_admin(filter_dict={"email":admin_data.email})
    if admin==None:
        new_admin= await create_admin(_with_default_access(admin_data))
        access_token, refresh_token = await issue_tokens_for_user(user_id=new_admin.id, role="admin")  # type: ignore
        new_admin.password=""
        new_admin.access_token= access_token
        new_admin.refresh_token = refresh_token
        return new_admin
    else:
        raise HTTPException(status_code=409,detail="Admin Already exists")

async def authenticate_admin(admin_data:AdminBase )->AdminOut:
    admin = await get_admin(filter_dict={"email":admin_data.email})

    if admin != None:
        if admin_data.password and check_password(password=admin_data.password,hashed=admin.password ):  # type: ignore
            admin.password=""
            access_token, refresh_token = await issue_tokens_for_user(user_id=admin.id, role="admin") # type: ignore
            admin.access_token=  access_token
            admin.refresh_token = refresh_token
            return admin
        else:
            raise HTTPException(status_code=401, detail="Unathorized, Invalid Login credentials")
    else:
        raise HTTPException(status_code=404,detail="Admin not found")

async def refresh_admin_tokens_reduce_number_of_logins(admin_refresh_data:AdminRefresh,expired_access_token):
    refreshObj= await get_refresh_tokens(admin_refresh_data.refresh_token)
    if refreshObj:
        if refreshObj.previousAccessToken==expired_access_token:
            admin = await get_admin(filter_dict={"_id":ObjectId(refreshObj.userId)})
            
            if admin!= None:
                    access_token, refresh_token = await issue_tokens_for_user(user_id=admin.id, role="admin") # type: ignore
                    admin.access_token= access_token
                    admin.refresh_token = refresh_token
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

async def update_admin_by_id(admin_id: str, admin_data: AdminUpdate,is_password_getting_changed:bool=False) -> AdminOut:
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
    if is_password_getting_changed==True:
        await delete_access_and_refresh_token_with_user_id(userId=admin_id)
    return result


def _public_account(document: dict) -> dict:
    account = {key: value for key, value in document.items() if key not in {"_id", "password"}}
    return {"id": str(document["_id"]), **account}


async def retrieve_role_accounts(role: str, start: int, stop: int) -> List[dict]:
    # Every account role (user, split roles, make-account roles) lives in the "<role>s" collection.
    cursor = db[f"{role}s"].find({}).skip(start).limit(stop - start)
    return [_public_account(document) async for document in cursor]


async def update_role_account_access(role: str, account_id: str, access: AccountAccessUpdate) -> dict:
    if not ObjectId.is_valid(account_id):
        raise HTTPException(status_code=400, detail="Invalid account ID format")
    changes = access.model_dump(exclude_none=True, mode="json")
    if not changes:
        raise HTTPException(status_code=400, detail="Provide permissionList and/or accountStatus")

    document = await db[f"{role}s"].find_one_and_update(
        {"_id": ObjectId(account_id)},
        {"$set": {**changes, "last_updated": int(time.time())}},
        return_document=ReturnDocument.AFTER,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if access.accountStatus not in (None, AccountStatus.ACTIVE):
        # Suspended or deactivated accounts lose their sessions immediately.
        await delete_access_and_refresh_token_with_user_id(userId=account_id)
    return _public_account(document)
