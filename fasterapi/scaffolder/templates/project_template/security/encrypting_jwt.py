import jwt
import datetime
from datetime import timezone
from core.database import db
from dotenv import load_dotenv
import os
import asyncio
from bson import ObjectId

load_dotenv()
SECRETID = os.getenv("SECRETID")


async def get_secret_dict()->dict:
    result =await db.secret_keys.find_one({"_id":ObjectId(SECRETID)})
    result.pop('_id')
    return result



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



async def create_jwt_member_token(token):
    secrets = await get_secret_and_header()
    SECRET_KEYS= secrets['SECRET_KEY']
    headers= secrets['HEADERS']
    
    payload = {
        'accessToken': token,
        'role':'member',
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=15)
    }
    
    
    token = jwt.encode(payload, SECRET_KEYS[headers['kid']], algorithm='HS256', headers=headers)

    return token

async def create_jwt_admin_token(token):
    secrets = await get_secret_and_header()
    SECRET_KEYS= secrets['SECRET_KEY']
    headers= secrets['HEADERS']
    
    payload = {
        'accessToken': token,
        'role':'admin',
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=15)
    }

    
    token = jwt.encode(payload, SECRET_KEYS[headers['kid']], algorithm='HS256', headers=headers)

    return token



async def decode_jwt_token(token):
    """_summary_

    Args:
        token (_type_): _description_

    Raises:
        Exception: _description_

    Returns:
        if decoded true: {'accessToken': '682c99f395ff4782fbea010f', 'role': 'admin', 'exp': 1747825460}
    """
    SECRET_KEYS = await get_secret_dict()
    # Decode header to extract the `kid`
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header['kid']

    # Look up the correct key
    key = SECRET_KEYS.get(kid)

    if not key:
        raise Exception("Unknown key ID")

    # Now decode and verify
    try:
        decoded = jwt.decode(token, key, algorithms=['HS256'])
        return decoded
    except jwt.exceptions.ExpiredSignatureError:
        print("expired token")
        return None
    except jwt.exceptions.InvalidSignatureError:
        print("invalid signature")
        return None
    except jwt.exceptions.DecodeError:
        print("Malformed Token")
        return None

async def decode_jwt_token_without_expiration(token):
    SECRET_KEYS = await get_secret_dict()
    # Decode header to extract the `kid`
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header['kid']

    # Look up the correct key
    key = SECRET_KEYS.get(kid)

    if not key:
        raise Exception("Unknown key ID")

    # Now decode and verify
    try:
        decoded = jwt.decode(token, key, algorithms=['HS256'])
        return decoded
    except jwt.exceptions.ExpiredSignatureError:
        print("expired token")
        payload = decoded = jwt.decode(token, key, algorithms=['HS256'],options={"verify_exp": False})
        return payload

    except jwt.exceptions.DecodeError:
        print("Malformed Token")
        return None




