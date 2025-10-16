from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class MainBotSettings(BaseSettings):
    tg_token: str
        
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env")