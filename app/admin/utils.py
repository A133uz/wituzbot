from typing import Optional
import datetime, jwt, boto3
from fastapi import Request, UploadFile, HTTPException
from passlib.context import CryptContext
from botocore.exceptions import ClientError
from .config import AdminSettings

import logging, uuid

settings = AdminSettings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.s3 = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        
    async def upload_image(self, file: UploadFile) -> str:
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=415, detail="Unsupported file type.")
        file_bytes = await file.read()
        ext = file.filename.split('.')[-1]
        filename = f"events/{uuid.uuid4()}.{ext}"
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=filename,
                Body=file_bytes,
                ContentType=file.content_type,
                ACL="public-read"
            )
        except ClientError as e:
            import traceback; 
            traceback.print_exc()
            logger.error(f"S3 upload error: {e} - Response: {getattr(e, 'response', None)}")
            raise HTTPException(status_code=500, detail="Image upload failed:")
        return f"https://{self.bucket}.s3.amazonaws.com/{filename}"
    
    def delete_image(self, image_url: str):
        if not image_url:
            return
        try:
            key = image_url.split(f"{self.bucket}.s3.amazonaws.com/")[-1]
            self.s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception as e:
            
            print(f"Failed to delete image: {e}")


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