from typing import Optional
import datetime, jwt, boto3
from fastapi import Request, UploadFile, HTTPException
import bcrypt
from botocore.exceptions import ClientError
from .config import AdminSettings

import logging, uuid

settings = AdminSettings()



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
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

# JWT token utilities
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire =  datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"Access token created with expiry: {expire.isoformat()}")
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"Token verified successfully for user: {payload.get('sub', 'unknown')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: token has expired")
        return None
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token verification failed: invalid token ({e})")
        return None
        
    except Exception as e:
        logger.error(f"Token verification failed with unexpected error: {e}")
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