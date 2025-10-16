from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class FeedbackBotSettings(BaseSettings):
    tg_token: str
    admin_chat_id: int
      
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env")