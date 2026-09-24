
from pymongo import ReturnDocument
from core.database import db
from fastapi import HTTPException,status
from typing import List,Optional
from schemas.admin_schema import AdminUpdate, AdminCreate, AdminOut
import os
from dotenv import load_dotenv
from security.hash import hash_password


load_dotenv()
SUPER_ADMIN_ID = "656f7ac12b9d4f6c9e2b9f7d"
SUPER_ADMIN_EMAIL=os.getenv("SUPER_ADMIN_EMAIL") 
SUPER_ADMIN_PASSWORD=os.getenv("SUPER_ADMIN_PASSWORD")
# The built-in super admin only exists when both values are set.
SUPER_ADMIN_ENABLED = bool(SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD)
SUPER_ADMIN_HASHED_PASSWORD = hash_password(SUPER_ADMIN_PASSWORD) if SUPER_ADMIN_ENABLED else None


def _super_admin() -> AdminOut:
    from security.permissions import default_permissions  # imported here to avoid a circular import

    return AdminOut(
        _id=SUPER_ADMIN_ID,
        full_name="Super Admin",
        email=SUPER_ADMIN_EMAIL,
        password=SUPER_ADMIN_HASHED_PASSWORD,
        permissionList=default_permissions(),
    )


def _is_super_admin_lookup(filter_dict: dict) -> bool:
    if not SUPER_ADMIN_ENABLED:
        return False
    return filter_dict.get("email") == SUPER_ADMIN_EMAIL or str(filter_dict.get("_id")) == SUPER_ADMIN_ID


async def create_admin(admin_data: AdminCreate) -> AdminOut:
    admin_dict = admin_data.model_dump(mode='json')
    result =await db.admins.insert_one(admin_dict)
    result = await db.admins.find_one(filter={"_id":result.inserted_id})
  
    returnable_result = AdminOut(**result)
    return returnable_result

async def get_admin(filter_dict: dict) -> Optional[AdminOut]:
    
    try:
        result = await db.admins.find_one(filter_dict)

        if result is None:
            return _super_admin() if _is_super_admin_lookup(filter_dict) else None

        return AdminOut(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching admin: {str(e)}"
        )
    
async def get_admins(filter_dict: dict = {},start=0,stop=100) -> List[AdminOut]:
    try:
        if filter_dict is None:
            filter_dict = {}

        cursor = (db.admins.find(filter_dict)
        .skip(start)
        .limit(stop - start)
        )
        admin_list = []

        async for doc in cursor:
            adminObj =AdminOut(**doc)
            adminObj.password=None
            admin_list.append(adminObj)
        if SUPER_ADMIN_ENABLED:
            admin_list.append(_super_admin())
        return admin_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching admins: {str(e)}"
        )
async def update_admin(filter_dict: dict, admin_data: AdminUpdate) -> AdminOut:
    result = await db.admins.find_one_and_update(
        filter_dict,
        {"$set": admin_data.model_dump()},
        return_document=ReturnDocument.AFTER
    )
    returnable_result = AdminOut(**result)
    return returnable_result

async def delete_admin(filter_dict: dict):
    return await db.admins.delete_one(filter_dict)