import jwt
 
from datetime import timedelta, timezone,datetime
from core.database import db
from core.settings import get_settings
from dotenv import load_dotenv
import os
from pydantic import BaseModel
from bson import ObjectId

load_dotenv()
SECRETID = os.getenv("SECRETID")

# Token lifetime (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES = 60
# Secret key for signing (use env var in production)


# ---------------------------
# JWT Schema
# ---------------------------
class JWTPayload(BaseModel):
    access_token: str
    user_id: str
    user_type: str
    is_activated: bool
    exp: datetime
    iat: datetime

SECRET_KEY = get_settings().secret_key or "dev-only-insecure-secret"
ALGORITHM = "HS256"

async def get_secret_dict()->dict:
    result =await db.secret_keys.find_one({"_id":ObjectId(SECRETID)})
    result.pop('_id') # type: ignore
    return result # type: ignore



async def get_secret_and_header():
    
    import random
    
    secrets = await get_secret_dict()
    
    random_key = random.choice(list(secrets.keys()))
    random_secret = secrets[random_key]
    SECRET_KEYS={random_key:random_secret}
    HEADERS = {"kid":random_key}
    result = {
        "SECRET_KEY":SECRET_KEYS,
        "HEADERS":HEADERS
    }
    
    return result


# ---------------------------
# Create Token
# ---------------------------
def create_jwt_token(
    access_token: str,
    user_id: str,
    user_type: str,
    is_activated: bool,
    role: str = "member",
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
        algorithm=ALGORITHM,   # "HS256"
        headers={"typ": "JWT"},
    )

    return token





async def create_jwt_member_token(token: str, userId: str):
    payload = {
        "accessToken": token,
        "role": "member",
        "userId": userId,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }

    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

async def create_jwt_admin_token(token: str,userId:str):
    payload = {
        "accessToken": token,
        "role": "admin",
        "userId":userId,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }

    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return encoded_jwt



async def decode_jwt_token(token: str):
    """
    Decodes and verifies a JWT token.

    Args:
        token (str): Encoded JWT token.

    Returns:
        dict | None: Decoded payload if valid, or None if invalid/expired.

    Example:
        {'accessToken': '682c99f395ff4782fbea010f', 'role': 'admin', 'exp': 1747825460}
    """

    try:
        # Decode and verify
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
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

    except Exception as e:
        print(f"Unexpected decode error: {e}")
        return None

async def decode_jwt_token_without_expiration(token: str):
    try:
        # Try decoding normally (with expiration check)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        return decoded
    
    except jwt.ExpiredSignatureError:
    
        try:
            # Decode again but skip exp validation
            decoded = jwt.decode(
                token, SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False}
            )
            return decoded
        except Exception as inner_e:
            print(f"Failed to decode expired token: {inner_e}")
            return None

    except jwt.DecodeError:
        print("Malformed token")
        return None

    except Exception as e:
        print(f"Unexpected error decoding token: {e}")
        return None




