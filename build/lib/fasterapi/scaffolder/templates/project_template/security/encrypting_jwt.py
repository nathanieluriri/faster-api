import os
from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from dotenv import load_dotenv
from pydantic import BaseModel

from core.database import db
from core.settings import get_settings

load_dotenv()
SECRETID = os.getenv("SECRETID")

# Token lifetime (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class JWTPayload(BaseModel):
    access_token: str
    user_id: str
    user_type: str
    is_activated: bool
    exp: datetime
    iat: datetime


SECRET_KEY = get_settings().secret_key or "dev-only-insecure-secret"
ALGORITHM = "HS256"


async def get_secret_dict() -> dict:
    result = await db.secret_keys.find_one({"_id": ObjectId(SECRETID)})
    result.pop("_id")
    return result


async def get_secret_and_header():
    import random

    secrets = await get_secret_dict()

    random_key = random.choice(list(secrets.keys()))
    random_secret = secrets[random_key]
    secret_keys = {random_key: random_secret}
    headers = {"kid": random_key}
    return {
        "SECRET_KEY": secret_keys,
        "HEADERS": headers,
    }


def create_jwt_token(
    access_token: str,
    user_id: str,
    user_type: str,
    is_activated: bool,
    role: str = "user",
) -> str:
    payload = JWTPayload(
        access_token=access_token,
        user_id=user_id,
        user_type=user_type,
        is_activated=is_activated,
        exp=datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        iat=datetime.now(timezone.utc),
    ).model_dump()

    payload["role"] = role

    token = jwt.encode(
        payload=payload,
        key=SECRET_KEY,
        algorithm=ALGORITHM,
        headers={"typ": "JWT"},
    )
    return token


async def create_jwt_role_token(token: str, user_id: str, role: str) -> str:
    payload = {
        "accessToken": token,
        "role": role,
        "userId": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_jwt_user_token(token: str, userId: str):
    return await create_jwt_role_token(token=token, user_id=userId, role="user")


async def create_jwt_member_token(token: str, userId: str):
    return await create_jwt_user_token(token=token, userId=userId)


async def create_jwt_admin_token(token: str, userId: str):
    return await create_jwt_role_token(token=token, user_id=userId, role="admin")


async def decode_jwt_token(token: str):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except jwt.ExpiredSignatureError:
        print("Expired token")
        return None
    except jwt.InvalidSignatureError:
        print("Invalid signature")
        return None
    except jwt.DecodeError:
        print("Malformed token")
        return None
    except Exception as exc:
        print(f"Unexpected decode error: {exc}")
        return None


async def decode_jwt_token_without_expiration(token: str):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except jwt.ExpiredSignatureError:
        try:
            decoded = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_exp": False},
            )
            return decoded
        except Exception as inner_exc:
            print(f"Failed to decode expired token: {inner_exc}")
            return None
    except jwt.DecodeError:
        print("Malformed token")
        return None
    except Exception as exc:
        print(f"Unexpected error decoding token: {exc}")
        return None
