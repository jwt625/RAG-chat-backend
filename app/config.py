from pydantic_settings import BaseSettings
from pydantic import SecretStr, Field
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "chatbot"  # default for development
    POSTGRES_PASSWORD: SecretStr = Field(default=SecretStr("dev_password_123"))
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "chatbot_db"

    # JWT
    JWT_SECRET_KEY: SecretStr = Field(default=SecretStr("dev_secret_key_123"))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # DeepSeek API
    DEEPSEEK_API_KEY: SecretStr = Field(
        ...,  # This makes it required
        description="DeepSeek API key for LLM completions. Get it from https://platform.deepseek.com"
    )

    # ChromaDB
    CHROMA_PERSIST_DIRECTORY: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/chromadb")

    # Text Processing
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    # CORS
    CORS_ORIGINS: list[str] = ["https://jwt625.github.io"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings() 