from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "sqlite:///./skillproof.db"
    GROQ_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
