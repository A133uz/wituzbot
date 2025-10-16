from typing import Optional
import datetime, jwt
from fastapi import Request
from passlib.context import CryptContext
from .config import AdminSettings

settings = AdminSettings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# JWT token utilities
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire =  datetime.datetime.now() + expires_delta
    else:
        expire = datetime.datetime.now() + datetime.timedelta(hours=settings.access_token_expire_hours)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except jwt.PyJWTError:
        return None
    
def get_flash_messages(request: Request) -> list:
    """Get flash messages from session"""
    messages = request.session.get("flash_messages", [])
    request.session["flash_messages"] = []  # Clear messages after getting them
    return messages

def flash_message(request: Request, message: str, category: str = "info"):
    """Add flash message to session"""
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append({"message": message, "category": category})