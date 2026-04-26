from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

    PHOTOS_DIR: str = "/app/photos"
    HF_CACHE: str = "~/.cache/huggingface"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 6000
    LLAMA_HOST: str = "localhost"
    LLAMA_PORT: int = 42069


@lru_cache
def get_settings() -> Settings:
    return Settings()
