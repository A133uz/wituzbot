from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class DatabaseSettings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    REDIS_URL: str
    
    
    @property
    def DATABASE_URL_asyncpg(self):
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def DATABASE_URL_syncpg(self):
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def DATABASE_URL_aiosqlite(self):
        return "sqlite+aiosqlite:///db.sqlite3"
    
    @property
    def DATABASE_URL_sqlite(self):
        return "sqlite:///db.sqlite3"
    
        
    model_config = SettingsConfigDict(env_file="/app/.env.database", extra='ignore')