
from fastapi import Depends, Request
from schemas.tokens_schema import accessTokenOut
from security.auth import verify_admin_token


async def log_what_admin_does(request: Request, token: accessTokenOut = Depends(verify_admin_token)):
    print("___________admin_log_function_starts_here___________")
    # Access token
    print("Token:", token)

    # Route path
    print("Route Path:", request.url.path)

    # Function name
    endpoint = request.scope["endpoint"]
    print("Function:", endpoint.__name__)
    print("___________admin_log_function_ends_here___________")
    
    
    
    
