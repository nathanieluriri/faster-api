
from pymongo import ReturnDocument
from core.database import db
from fastapi import HTTPException,status
from typing import List,Optional
from schemas.user_schema import UserUpdate, UserCreate, UserOut

async def create_user(user_data: UserCreate) -> UserOut:
    user_dict = user_data.model_dump()
    result =await db.users.insert_one(user_dict)
    result = await db.users.find_one(filter={"_id":result.inserted_id})
  
    returnable_result = UserOut(**result)
    return returnable_result

async def get_user(filter_dict: dict) -> Optional[UserOut]:
    try:
        result = await db.users.find_one(filter_dict)

        if result is None:
            return None

        return UserOut(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching user: {str(e)}"
        )
    
async def get_users(filter_dict: dict = {},start=0,stop=100) -> List[UserOut]:
    try:
        if filter_dict is None:
            filter_dict = {}

        cursor = (db.users.find(filter_dict)
        .skip(start)
        .limit(stop - start)
        )
        user_list = []

        async for doc in cursor:
            userObj =UserOut(**doc)
            userObj.password=None
            user_list.append(userObj)
        
        return user_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users: {str(e)}"
        )
async def update_user(filter_dict: dict, user_data: UserUpdate) -> UserOut:
    result = await db.users.find_one_and_update(
        filter_dict,
        {"$set": user_data.model_dump()},
        return_document=ReturnDocument.AFTER
    )
    returnable_result = UserOut(**result)
    return returnable_result

async def delete_user(filter_dict: dict):
    return await db.users.delete_one(filter_dict)