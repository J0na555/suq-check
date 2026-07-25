from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SuqCheck API"
    environment: str = "development"
    cors_origins: str = "*"
    use_fixtures: bool = True
    database_url: str = ""
    migration_database_url: str = ""
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_echo: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

