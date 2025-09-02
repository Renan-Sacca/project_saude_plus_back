import hashlib

def hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

def check_pwd(pwd: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return hash_pwd(pwd) == hashed
