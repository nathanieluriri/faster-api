
from fastapi import APIRouter, HTTPException, Query, status, Path,Depends,Body
from typing import List,Annotated
from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from schemas.admin_schema import (
    AdminCreate,
    AdminOut,
    AdminBase,
    AdminUpdate,
    AdminRefresh,
    AdminLogin
)
from services.admin_service import (
    add_admin,
    remove_admin,
    retrieve_admins,
    authenticate_admin,
    retrieve_admin_by_admin_id,
    update_admin,
    refresh_admin_tokens_reduce_number_of_logins,

)
from security.auth import verify_token,verify_token_to_refresh,verify_admin_token
router = APIRouter(prefix="/admins", tags=["Admins"])

@router.get(
    "/{start}/{stop}", 
    response_model=APIResponse[List[AdminOut]],
    response_model_exclude_none=True,
    response_model_exclude={"data": {"__all__": {"password"}}},
    dependencies=[Depends(verify_admin_token)]
)
async def list_admins(
    # Use Path and Query for explicit documentation/validation of GET parameters
    start: Annotated[
        int,
        Path(ge=0, description="The starting index (offset) for the list of admins.")
    ] , 
    stop: Annotated[
        int, 
        Path(gt=0, description="The ending index for the list of admins (limit).")
    ] 
):
    """
    **ADMIN ONLY:** Retrieves a paginated list of all registered admins.

    **Authorization:** Requires a **valid Access Token** (Admin role) in the 
    `Authorization: Bearer <token>` header.

    ### Examples (Illustrative URLs):

    * **First Page:** `/admins/0/5` (Start at index 0, retrieve up to 5 admins)
    * **Second Page:** `/admins/5/10` (Start at index 5, retrieve up to 5 more admins)
    
    """
    
    # Note: The code below overrides the path parameters with hardcoded defaults (0, 100).
    # You should typically use the passed parameters: 
    # items = await retrieve_admins(start=start, stop=stop)
    
    # Using the hardcoded values from your original code:
    items = await retrieve_admins(start=0, stop=100)
    
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")


@router.get(
    "/me", 
    response_model=APIResponse[AdminOut],
    dependencies=[Depends(verify_admin_token)],
    response_model_exclude_none=True,
    response_model_exclude={"data": {"password"}},
)
async def get_my_admin(
    token: accessTokenOut = Depends(verify_admin_token),
        
):
    """
    Retrieves the profile information for the currently authenticated admin.

    The admin's ID is automatically extracted from the valid Access Token 
    in the **Authorization: Bearer <token>** header.
    """
    
    items = await retrieve_admin_by_admin_id(id=token.get("userId"))
    return APIResponse(status_code=200, data=items, detail="admins items fetched")





@router.post("/signup",response_model_exclude_none=True, response_model_exclude={"data": {"password"}},response_model=APIResponse[AdminOut])
async def signup_new_admin(
    
    admin_data: Annotated[
        AdminBase,
        Body(
            openapi_examples={
                "admin Signup": {
                    "summary": "Admin Signup Example",
                    "description": "Example payload for a **Admin** registering on the platform.",
                    "value": {
                        "full_name": "Admin Base",
                        "password": "securepassword123",
                        "email": "admin@secure.com"
                    },
                },
              
            }
        ),
    ],
    token: accessTokenOut = Depends(verify_admin_token),
):
 
    admin_data_dict = admin_data.model_dump() 
    new_admin = AdminCreate(
      invited_by=token.get("userId"),
        **admin_data_dict
    )
    items = await add_admin(admin_data=new_admin)
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")

@router.post("/login",response_model_exclude={"data": {"password"}}, response_model_exclude_none=True,response_model=APIResponse[AdminOut])
async def login_admin(
    admin_data: Annotated[
        AdminLogin,
        Body(
            openapi_examples={
                "successful_login": {
                    "summary": "Successful Login",
                    "description": "Standard payload for a successful authentication attempt.",
                    "value": {
                        "email": "admin@registered.com",
                        "password": "securepassword123",
                    },
                },
                "unauthorized_login": {
                    "summary": "Unauthorized Login (Wrong Password)",
                    "description": "Payload that would result in a **401 Unauthorized** error due to incorrect credentials.",
                    "value": {
                        "email": "admin@registered.com",
                        "password": "wrongpassword999", # Intentionally incorrect
                    },
                },
                "invalid_email_format": {
                    "summary": "Invalid Email Format",
                    "description": "Payload that would trigger a **422 Unprocessable Entity** error due to Pydantic validation failure (not a valid email address).",
                    "value": {
                        "email": "not-an-email-address", # Pydantic will flag this
                        "password": "anypassword",
                    },
                },
            }
        ),
    ]
):
    """
    Authenticates a admin with the provided email and password.
    
    Upon success, returns the authenticated admin data and an authentication token.
    """
    items = await authenticate_admin(admin_data=admin_data)
    # The `authenticate_admin` function should raise an HTTPException 
    # (e.g., 401 Unauthorized) on failure.
    
    return APIResponse(status_code=200, data=items, detail="Fetched successfully")



@router.post(
    "/refresh",
    response_model=APIResponse[AdminOut],
    dependencies=[Depends(verify_token_to_refresh)],
    response_model_exclude={"data": {"password"}},
)
async def refresh_admin_tokens(
    admin_data: Annotated[
        AdminRefresh,
        Body(
            openapi_examples={
                "successful_refresh": {
                    "summary": "Successful Token Refresh",
                    "description": (
                        "The correct payload for refreshing tokens. "
                        "The **expired access token** is provided in the `Authorization: Bearer <token>` header."
                    ),
                    "value": {
                        # A long-lived, valid refresh token
                        "refresh_token": "valid.long.lived.refresh.token.98765"
                    },
                },
                "invalid_refresh_token": {
                    "summary": "Invalid Refresh Token",
                    "description": (
                        "Payload that would fail the refresh process because the **refresh_token** "
                        "in the body is invalid or has expired."
                    ),
                    "value": {
                        "refresh_token": "expired.or.malformed.refresh.token.00000"
                    },
                },
                "mismatched_tokens": {
                    "summary": "Tokens Belong to Different Admins",
                    "description": (
                        "A critical security failure example: the refresh token in the body "
                        "does not match the admin ID associated with the expired access token in the header. "
                        "This should result in a **401 Unauthorized**."
                    ),
                    "value": {
                        "refresh_token": "refresh.token.of.different.admin.77777"
                    },
                },
            }
        ),
    ],
    token: accessTokenOut = Depends(verify_token_to_refresh)
):
    """
    Refreshes the admin's access token and returns a new token pair.

    Requires an **expired access token** in the Authorization header and a **valid refresh token** in the body.
    """
    print("itemsssssssssssssssssssssssssssssssssssssssssss")
    print(token)
    items = await refresh_admin_tokens_reduce_number_of_logins(
        admin_refresh_data=admin_data,
        expired_access_token=token.accesstoken
    )
    
    # Clears the password before returning, which is good practice.
    items.password = ''
    
    return APIResponse(status_code=200, data=items, detail="admins items fetched")


@router.delete("/account", dependencies=[Depends(verify_admin_token)], response_model_exclude_none=True)
async def delete_admin_account(
    token: accessTokenOut = Depends(verify_token),
    # Use Body to host the openapi_examples, even if the payload is empty
    # We use a simple dictionary here since there is no Pydantic model for the body
    _body: Annotated[
        dict,
        Body(
            openapi_examples={
                "successful_deletion": {
                    "summary": "Successful Account Deletion",
                    "description": (
                        "A successful request **requires no body** and relies entirely on a **valid, non-expired Access Token** "
                        "in the `Authorization: Bearer <token>` header to identify the admin."
                    ),
                    "value": {},  # Empty body
                },
                "unauthorized_deletion": {
                    "summary": "Unauthorized Deletion (Invalid Token)",
                    "description": (
                        "This scenario represents a request where the **Access Token is missing, expired, or invalid**. "
                        "The `verify_token` dependency should intercept this and return a **401 Unauthorized**."
                    ),
                    "value": {},  # Empty body
                },
            }
        ),
    ] = {}, # Default empty dictionary for the body
):
    """
    Deletes the account associated with the provided access token.

    The admin ID is extracted from the valid Access Token in the Authorization header.
    No request body is required.
    """
    result = await remove_admin(admin_id=token.userId)
    
    # The 'result' is assumed to be a standard FastAPI response object or a dict/model 
    # that is automatically converted to a response.
    return result