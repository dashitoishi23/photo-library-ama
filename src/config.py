from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="src/.env",
        env_file_encoding="utf-8",
    )

    PHOTOS_DIR: str = "/app/photos"
    HF_CACHE: str = "~/.cache/huggingface"
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
