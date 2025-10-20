from schemas.tokens_schema import refreshTokenOut,accessTokenOut,refreshTokenCreate,accessTokenCreate
from security.encrypting_jwt import create_jwt_admin_token,create_jwt_member_token,decode_jwt_token,decode_jwt_token_without_expiration
from bson import errors,ObjectId
from fastapi import HTTPException,status
from security.encrypting_jwt import decode_jwt_token




async def generate_member_access_tokens(userId)->accessTokenOut:
    from repositories.tokens_repo import add_user_access_token

    
    try:
        obj_id = ObjectId(userId)
    except errors.InvalidId:
        raise   HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid User Id")    

    new_access_token = await add_user_access_token(token_data=accessTokenCreate(userId=userId))
    new_access_token.accesstoken = await create_jwt_member_token(token=new_access_token.accesstoken)
    
    return new_access_token



async def generate_admin_access_tokens(userId)->accessTokenOut:
    from repositories.tokens_repo import add_admin_access_tokens

    try:
        obj_id = ObjectId(userId)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid User Id")    # or raise an error / log it    

    new_access_token = await add_admin_access_tokens(token_data=accessTokenCreate(userId=userId))
    new_access_token.accesstoken = await create_jwt_admin_token(token=new_access_token.accesstoken,userId=userId)
    return new_access_token
    
    
    
async def generate_refresh_tokens(userId,accessToken)->refreshTokenOut:
    from repositories.tokens_repo import add_refresh_tokens

    try:
        obj_id = ObjectId(userId)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid User Id While trying to create refresh token")    # or raise an error / log it    

    accessToken = await decode_jwt_token(accessToken)
    if accessToken==None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Failed to decode the accesstoken while trying to create a refreshtoken")
    try:
        obj_id = ObjectId(accessToken['accessToken'])
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Access Id While trying to create refresh token")    # or raise an error / log it    

    new_refresh_token =await add_refresh_tokens(token_data=refreshTokenCreate(userId=userId,previousAccessToken=accessToken['accessToken']))
    return new_refresh_token


async def validate_refreshToken(refreshToken:str):
    from repositories.tokens_repo import get_refresh_tokens

    try:
        obj_id = ObjectId(refreshToken)
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Refresh Id")   # or raise an error / log it    

    refresh_token = await get_refresh_tokens(refreshToken=refreshToken)
    if refresh_token:
        new_refresh_token = await generate_refresh_tokens(userId=refresh_token.userId,accessToken=refresh_token.previousAccessToken)
        return new_refresh_token
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Refresh Id")
    


async def validate_member_accesstoken(accessToken:str):
    from repositories.tokens_repo import get_access_token

    decodedAccessToken = await decode_jwt_token(token=accessToken)
    try:
        obj_id = ObjectId(decodedAccessToken['accessToken'])
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Access Token")   # or raise an error / log it    
    except TypeError:
        return None

    
    if decodedAccessToken:
        validatedAccessToken= await get_access_token(accessToken=decodedAccessToken['accessToken'])
    
        if validatedAccessToken:
            return validatedAccessToken
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Access Tokens While Validating Member Access Tokens")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Refresh Tokens While Validating Member Access Tokens")
    
    
async def validate_admin_accesstoken_otp(accessToken:str):
    from repositories.tokens_repo import get_inactive_access_token

    decodedAccessToken = await decode_jwt_token(token=accessToken)
    print(decodedAccessToken)
    try:
        obj_id = ObjectId(decodedAccessToken['accessToken'])
    except errors.InvalidId:
        
        return None  # or raise an error / log it    

    print("o1")
    if decodedAccessToken:
       
        if decodedAccessToken['role']=="admin":
           
            validatedAccessToken= await get_inactive_access_token(token_id=decodedAccessToken['accessToken'])
            print(validatedAccessToken)
            if type(validatedAccessToken) == type(accessTokenOut(userId="12",accesstoken="sa")):
                return validatedAccessToken
            elif validatedAccessToken=="None":
                return None
            else:
                return "active" 
        else:
            return None  
        
    else:
        print("o4")
        return None 
    
async def validate_admin_accesstoken(accessToken:str):
     
    from repositories.tokens_repo import get_admin_access_tokens
    decodedAccessToken = await decode_jwt_token(token=accessToken)
    print(decodedAccessToken)
    try:
        obj_id = ObjectId(decodedAccessToken['accessToken'])
    except errors.InvalidId:
        
        return None  # or raise an error / log it    

    print("o1")
    if decodedAccessToken:
       
        if decodedAccessToken['role']=="admin":
           
            validatedAccessToken= await get_admin_access_tokens(token_id=decodedAccessToken['accessToken'])
            print(validatedAccessToken)
            if type(validatedAccessToken) == type(accessTokenOut(userId="12",accesstoken="sa")):
                return validatedAccessToken
            elif validatedAccessToken=="None":
                return None
            else:
                return "inactive" 
        else:
            return None  
        
    else:
        print("o4")
        return None 
    
    
async def validate_expired_admin_accesstoken(accessToken:str):
    from repositories.tokens_repo import get_admin_access_tokens

    decodedAccessToken = await decode_jwt_token_without_expiration(token=accessToken)
    try:
        obj_id = ObjectId(decodedAccessToken['accessToken'])
    except errors.InvalidId:
        return None  # or raise an error / log it    

    
    if decodedAccessToken:
        if decodedAccessToken['role']=="admin":
            validatedAccessToken= await get_admin_access_tokens(accessToken=decodedAccessToken['accessToken'])
            if type(validatedAccessToken) == type(accessTokenOut(userId="12",accesstoken="sa")):
                return validatedAccessToken
            elif validatedAccessToken=="None":
                return None
            else:
                return "inactive" 
        else:
            return None  
        
    else:
        return None 
    
    
    
    
    
    
    
    
async def validate_member_accesstoken_without_expiration(accessToken:str):
    from repositories.tokens_repo import get_access_token
    decodedAccessToken = await decode_jwt_token_without_expiration(token=accessToken)
    try:
        obj_id = ObjectId(decodedAccessToken['accessToken'])
    except errors.InvalidId:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Access Id")   # or raise an error / log it    

    
    if decodedAccessToken:
        validatedAccessToken= await get_access_token(accessToken=decodedAccessToken['accessToken'])
        if validatedAccessToken:
            return validatedAccessToken
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Refresh Id")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Couldn't Find Refresh Id")
    