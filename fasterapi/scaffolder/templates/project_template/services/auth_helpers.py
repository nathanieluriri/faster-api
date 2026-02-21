from repositories.tokens_repo import (
    add_access_tokens,
    add_admin_access_tokens,
    add_refresh_tokens,
    accessTokenCreate,
    refreshTokenCreate,
)
from security.encrypting_jwt import create_jwt_admin_token, create_jwt_member_token


async def issue_tokens_for_user(user_id: str, role: str) -> tuple[str, str]:
    if role == "admin":
        access_token = await add_admin_access_tokens(token_data=accessTokenCreate(userId=user_id))
        jwt_token = await create_jwt_admin_token(token=access_token.accesstoken, userId=user_id) # type: ignore
    else:
        access_token = await add_access_tokens(token_data=accessTokenCreate(userId=user_id))
        jwt_token = await create_jwt_member_token(token=access_token.accesstoken, userId=user_id) # type: ignore

    refresh_token = await add_refresh_tokens(
        token_data=refreshTokenCreate(userId=user_id, previousAccessToken=access_token.accesstoken) # type: ignore
    )

    return jwt_token, refresh_token.refreshtoken # type: ignore
