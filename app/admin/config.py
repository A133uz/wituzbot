from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr
from pathlib import Path


class AdminSettings(BaseSettings):
    # db_host: str
    # db_port: int
    # db_user: str
    # db_pass: str
    # db_name: str
    
    ADMIN_NAME: str
    ADMIN_LOGIN: str
    ADMIN_EMAIL: EmailStr
    ADMIN_PASS: str
    ADMIN_IS_SUPERUSER: bool
    ADMIN_IS_ACTIVE: bool 
    
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_HOURS: int
    
    CORS_ALLOWED_ORIGINS: str = "*"
    
    # @property
    # def DATABASE_URL_asyncpg(self):
    #     return f"postgresql+psycopg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    # 
    # @property
    # def DATABASE_URL_aiosqlite(self):
    #     return "sqlite+aiosqlite:///db.sqlite3"
    # 
    # @property
    # def DATABASE_URL_sqlite(self):
    #     return "sqlite:///db.sqlite3"
    
        
    model_config = SettingsConfigDict(env_file="/app/.env.admin")