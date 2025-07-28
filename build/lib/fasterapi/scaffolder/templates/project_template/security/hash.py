import bcrypt

def hash_password(password: str|bytes) -> bytes:
    if type(password)==str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed




def check_password(password: str, hashed: bytes) -> bool:

    return bcrypt.checkpw(password.encode('utf-8'), hashed)
