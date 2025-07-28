from core.database import db

from schemas.tokens_schema import accessTokenCreate,refreshTokenCreate,accessTokenOut,refreshTokenOut
import asyncio
from datetime import datetime, timedelta
from dateutil import parser
from bson import ObjectId,errors
from fastapi import HTTPException

async def add_access_tokens(token_data:accessTokenCreate)->accessTokenOut:
    token = token_data.model_dump()
    token['role']="member"
    result = await db.accessToken.insert_one(token)
    tokn = await db.accessToken.find_one({"_id":result.inserted_id})
    accessToken = accessTokenOut(**tokn)
    
    return accessToken 
    

async def add_admin_access_tokens(token_data:accessTokenCreate)->accessTokenOut:
    token = token_data.model_dump()
    token['role']="admin"
    token['status']="inactive"
    result = await db.accessToken.insert_one(token)
    tokn = await db.accessToken.find_one({"_id":result.inserted_id})
    accessToken = accessTokenOut(**tokn)
    
    return accessToken 

async def update_admin_access_tokens(token:str)->accessTokenOut:
    updatedToken= await db.accessToken.find_one_and_update(filter={"_id":ObjectId(token)},update={"$set": {'status':'active'}},return_document=True)
    accessToken = accessTokenOut(**updatedToken)
    return accessToken
    
async def add_refresh_tokens(token_data:refreshTokenCreate)->refreshTokenOut:
    token = token_data.model_dump()
    result = await db.refreshToken.insert_one(token)
    tokn = await db.refreshToken.find_one({"_id":result.inserted_id})
    refreshToken = refreshTokenOut(**tokn)
    return refreshToken

async def delete_access_token(accessToken):
    # await db.refreshToken.delete_many({"previousAccessToken":accessToken})
    await db.accessToken.find_one_and_delete({'_id':ObjectId(accessToken)})
    
    
async def delete_refresh_token(refreshToken:str):
    try:
        obj_id=ObjectId(refreshToken)
    except errors.InvalidId:
        raise HTTPException(status_code=401,detail="Invalid Refresh Id")
    result = await db.refreshToken.find_one_and_delete({"_id":obj_id})
    if result:
        return True



def is_older_than_days(date_string, days=10):
    # Parse the ISO 8601 date string into a datetime object
    created_date = parser.isoparse(date_string)

    # Get the current time in UTC
    now = datetime.utcnow().replace(tzinfo=created_date.tzinfo)

    # Check if the difference is greater than the given number of days
    return (now - created_date) > timedelta(days=days)



async def get_access_tokens(accessToken:str):
    
    token = await db.accessToken.find_one({"_id": ObjectId(accessToken)})
    if token:
        if is_older_than_days(date_string=token['dateCreated'])==False:
            if token.get("role",None)=="member":
                tokn = accessTokenOut(**token)
                return tokn
            elif token.get("role",None)=="admin":
                if token.get('status',None)=="active":
                    tokn = accessTokenOut(**token)
                    return tokn
                else: 
                    return None
            else:
                return None
            
        else:
            delete_access_token(accessToken=str(token['_id'])) 
            return None
    else:
        print("No token found")
        return "None"
    
    
async def get_refresh_tokens(refreshToken:str):
    token = await db.refreshToken.find_one({"_id": ObjectId(refreshToken)})
    if token:
        tokn = refreshTokenOut(**token)
        return tokn

    else: return None
    
    
    
async def delete_all_tokens_with_user_id(userId:str):
    await db.refreshToken.delete_many(filter={"userId":userId})
    await db.accessToken.delete_many(filter={"userId":userId})