from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class MainBotSettings(BaseSettings):
    TG_TOKEN: str
        
    model_config = SettingsConfigDict(env_file="/app/.env.mainbot")