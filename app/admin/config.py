from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr
from pathlib import Path


class AdminSettings(BaseSettings):
    # db_host: str
    # db_port: int
    # db_user: str
    # db_pass: str
    # db_name: str
    
    admin_name: str
    admin_login: str
    admin_email: EmailStr
    admin_pass: str
    admin_is_superuser: bool
    admin_is_active: bool 
    
    secret_key: str
    algorithm: str
    access_token_expire_hours: int
    
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
    
        
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env")