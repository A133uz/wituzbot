from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class Settings(BaseSettings):
    tg_token: str
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    redis_url: str
    
    admin_secret: str
    admin_site_name: str
    admin_user_model: str
    admin_user_model_username_field: str
    ADMIN_SITE_SIGN_IN_LOGO: str
    ADMIN_SITE_HEADER_LOGO: str
    ADMIN_PRIMARY_COLOR: str
    ADMIN_SESSION_EXPIRED_AT: int
    
    
    @property
    def DATABASE_URL_asyncpg(self):
        return f"postgresql+psycopg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def DATABASE_URL_aiosqlite(self):
        return "sqlite+aiosqlite:///db.sqlite3"
    
        
    model_config = SettingsConfigDict(env_file=".env")
    
settings = Settings()