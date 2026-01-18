# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from security.tokens import validate_admin_accesstoken,validate_admin_accesstoken_otp,generate_refresh_tokens,generate_member_access_tokens, validate_member_accesstoken, validate_refreshToken,validate_member_accesstoken_without_expiration,generate_admin_access_tokens,validate_expired_admin_accesstoken
from security.encrypting_jwt import decode_jwt_token
from repositories.tokens_repo import get_access_token, get_access_token_allow_expired
from schemas.tokens_schema import refreshedToken,accessTokenOut
from services.user_service import retrieve_user_by_user_id
 


token_auth_scheme = HTTPBearer()

# async def verify_token(token: str = Depends(token_auth_scheme))->accessTokenOut:
#     decoded_token = await decode_jwt_token(token=token.credentials)
    
#     if decoded_token['user_type']=="RIDER":
        
#         RIDER = await retrieve_rider_by_rider_id(id=decoded_token['user_id'])
#         if RIDER:
#             return JWTPayload(**decoded_token)
#     elif decoded_token['user_type']=="DRIVER":
#         DRIVER = await retrieve_driver_by_driver_id(id=decoded_token['user_id'])
#         if DRIVER:
#             return JWTPayload(**decoded_token)
#     elif decoded_token==None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token"
#         )
     
            
            


            
async def verify_token_to_refresh(token: str = Depends(token_auth_scheme)):
    result = await get_access_token_allow_expired(accessToken=token.credentials)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    else:
        return result
    
    

async def verify_token_user_role(token: str = Depends(token_auth_scheme)) -> accessTokenOut:
    try:
        result = await get_access_token(accessToken=token.credentials)
        if result is None or result.role != "member":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        user = await retrieve_user_by_user_id(id=result.userId)
        if user and result is not None:
            return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token :{e}",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


async def verify_token(token: str = Depends(token_auth_scheme)) -> accessTokenOut:
    return await verify_token_user_role(token=token)
 
        
      
async def verify_admin_token(token: str = Depends(token_auth_scheme)):
    from repositories.tokens_repo import get_admin_access_tokens
    
    try:
        decoded_access_token = await decode_jwt_token(token=token.credentials)
        if not decoded_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token",
            )
        if decoded_access_token.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token",
            )
        print("")
        print("")
      
        print("")
        print("")
        result = await get_admin_access_tokens(accessToken=token.credentials)

        if result==None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token"
            )
        elif isinstance(result, accessTokenOut):
            return decoded_access_token
    except TypeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Access Token Expired")
    
    
           
async def verify_admin_token_otp(token: str = Depends(token_auth_scheme)):
    try:
        result = await validate_admin_accesstoken_otp(accessToken=str(token.credentials))

        if result==None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token"
            )
        elif result=="active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin Token has been activated"
            )
        elif isinstance(result, accessTokenOut):
            
            decoded_access_token = await decode_jwt_token(token=token.credentials)
            return decoded_access_token
    except TypeError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Access Token Expired")
 
