# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from security.tokens import validate_admin_accesstoken,validate_admin_accesstoken_otp,generate_refresh_tokens,generate_member_access_tokens, validate_member_accesstoken, validate_refreshToken,validate_member_accesstoken_without_expiration,generate_admin_access_tokens,validate_expired_admin_accesstoken
from security.encrypting_jwt import decode_jwt_token,decode_jwt_token_without_expiration
from repositories.tokens_repo import get_access_tokens,get_access_tokens_no_date_check,get_agent_access_tokens,get_client_access_tokens
from schemas.tokens_schema import refreshedToken,accessTokenOut


token_auth_scheme = HTTPBearer()

async def verify_token(token: str = Depends(token_auth_scheme))->accessTokenOut:
    result = await get_access_tokens(accessToken=token.credentials)
    
    if result==None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    else:
        return result
            
            



async def verify_client_token(token: str = Depends(token_auth_scheme))->accessTokenOut:
    result = await get_client_access_tokens(accessToken=token.credentials)
    
    if result==None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    else:
        return result
            
            
async def verify_agent_token(token: str = Depends(token_auth_scheme))->accessTokenOut:
    result = await get_agent_access_tokens(accessToken=token.credentials)
    
    if result==None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    else:
        return result
            
            
async def verify_token_to_refresh(token: str = Depends(token_auth_scheme)):
    result = await get_access_tokens_no_date_check(accessToken=token.credentials)
    
    if result==None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    else:
        return result
        
        
      
async def verify_admin_token(token: str = Depends(token_auth_scheme)):
    from repositories.tokens_repo import get_admin_access_tokens
    
    try:
        decoded_access_token = await decode_jwt_token(token=token.credentials)
        print("")
        print("")
        print(decoded_access_token['accessToken'])
        print("")
        print("")
        result = await get_admin_access_tokens(accessToken=decoded_access_token['accessToken'])

        if result==None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token"
            )
        elif result=="inactive":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin Token hasn't been activated"
            )
        elif isinstance(result, accessTokenOut):
            
            decoded_access_token = await decode_jwt_token(token=token.credentials)
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


async def verify_any_token(token:str=Depends(token_auth_scheme)):
    token_type = await decode_jwt_token(token=token.credentials)
    if isinstance(token_type,dict):
        if token_type['role']=='admin':
            return await verify_admin_token(token=token)
        elif token_type["role"]=='member':
            return await verify_token(token=token)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token Type"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token"
        )