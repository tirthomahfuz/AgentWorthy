"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://agentworthy:agentworthy@localhost:5432/agentworthy"
    redis_url: str = "redis://localhost:6379/0"
    api_secret_key: str = "dev-secret-key"
    cors_origins: str = "http://localhost:3000"
    free_scans_per_day: int = 3
    free_crawl_max_pages: int = 25


@lru_cache
def get_settings() -> Settings:
    return Settings()
