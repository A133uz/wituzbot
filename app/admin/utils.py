from typing import Optional
import datetime, jwt
from fastapi import Request
from passlib.context import CryptContext
from .config import AdminSettings

import logging

settings = AdminSettings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# JWT token utilities
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire =  datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
        
    logger.info(f"DEBUG: Token expiry time (UTC): {expire}")
    logger.info(f"DEBUG: Current time (UTC): {datetime.datetime.now(datetime.timezone.utc)}")
    logger.info(f"DEBUG: Token data: {to_encode}")
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        logger.info(f"DEBUG: Verifying token (first 30 chars): {token[:30]}...")
        logger.info(f"DEBUG: Using algorithm: {settings.ALGORITHM}")
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        logger.info(f"DEBUG: Token verified successfully! Payload: {payload}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.error("DEBUG: Token has EXPIRED")
        return None
        
    except jwt.InvalidTokenError as e:
        logger.error(f"DEBUG: Invalid token: {e}")
        return None
        
    except Exception as e:
        logger.error(f"DEBUG: Unexpected error verifying token: {e}")
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