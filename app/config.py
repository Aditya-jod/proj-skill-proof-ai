import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables.
    """
    APP_NAME: str = "SkillProof AI"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/skillproof.db")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()
