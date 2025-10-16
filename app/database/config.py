from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class DatabaseSettings(BaseSettings):
    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    redis_url: str
    
    @property
    def DATABASE_URL_asyncpg(self):
        return f"postgresql+psycopg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def DATABASE_URL_aiosqlite(self):
        return "sqlite+aiosqlite:///db.sqlite3"
    
    @property
    def DATABASE_URL_sqlite(self):
        return "sqlite:///db.sqlite3"
    
        
    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent.parent / ".env")