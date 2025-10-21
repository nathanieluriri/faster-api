from core.database import db

from schemas.tokens_schema import accessTokenCreate,refreshTokenCreate,accessTokenOut,refreshTokenOut
import asyncio
from datetime import datetime, timezone, timedelta
from dateutil import parser
from bson import ObjectId,errors
from fastapi import HTTPException
from repositories.admin_repo import get_admin
from security.encrypting_jwt import decode_jwt_token_without_expiration

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
    token['status']="active"
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



def is_older_than_days(date_value, days=10):
    """
    Accepts either an ISO-8601 string or a UNIX timestamp (int/float).
    Returns True if older than `days` days.
    """
    # Determine type and parse accordingly
    if isinstance(date_value, (int, float)):
        # It's a UNIX timestamp (seconds)
        created_date = datetime.fromtimestamp(date_value, tz=timezone.utc)
    else:
        # Assume ISO string
        created_date = parser.isoparse(str(date_value))

    # Get the current time in UTC (with same tzinfo)
    now = datetime.now(timezone.utc)

    # Check if the difference is greater than the given number of days
    return (now - created_date) > timedelta(days=days)


async def get_access_tokens(accessToken:str)->accessTokenOut:
    
    token = await db.accessToken.find_one({"_id": ObjectId(accessToken)})
    if token:
        if is_older_than_days(date_value=token['dateCreated'])==False:
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
    
    
    
async def get_admin_access_tokens(accessToken:str)->accessTokenOut:
    
    token = await db.accessToken.find_one({"_id": ObjectId(accessToken)})
    print(token)
    if token:
        if is_older_than_days(date_value=token['dateCreated'])==False:
            if token.get("role",None)=="admin":
                userId = token.get("userId")
                if await get_admin(filter_dict={"_id":ObjectId(userId)}):
                
                    tokn = accessTokenOut(**token)
                    return tokn
                else:
                    print("not an admin access token")
                    
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
        print("No token foundddd")
        return None
   
    
        
from bson.errors import InvalidId

async def get_access_tokens_no_date_check(accessToken: str) -> accessTokenOut | None:
    try:
        # Try interpreting the token as an ObjectId
        object_id = ObjectId(accessToken)
        token = await db.accessToken.find_one({"_id": object_id})
    except (InvalidId, TypeError):
        # If it's not a valid ObjectId, fall back to decoding the token
        token = await decode_jwt_token_without_expiration(accessToken)
        print("hereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        print(token)

    if not token:
        print("No token found")
        return None

    role = token.get("role")
    status = token.get("status")

    if role == "member":
        return accessTokenOut(**token)
    elif role == "admin":
       return accessTokenOut(**token)
    else:
        return None

    
async def get_refresh_tokens(refreshToken:str)->refreshTokenOut:
    token = await db.refreshToken.find_one({"_id": ObjectId(refreshToken)})
    if token:
        tokn = refreshTokenOut(**token)
        return tokn

    else: return None
    
    
    
async def delete_all_tokens_with_user_id(userId:str):
    await db.refreshToken.delete_many(filter={"userId":userId})
    await db.accessToken.delete_many(filter={"userId":userId})
    
async def delete_all_tokens_with_admin_id(adminId:str):
    await db.refreshToken.delete_many(filter={"userId":adminId})
    await db.accessToken.delete_many(filter={"userId":adminId})