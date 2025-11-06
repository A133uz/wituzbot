from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class FeedbackBotSettings(BaseSettings):
    TG_TOKEN: str
    ADMIN_CHAT_ID: int
      
    model_config = SettingsConfigDict(env_file="/app/.env.feedback_bot")