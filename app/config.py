"""Application configuration via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://nso:nso_dev@localhost:5432/nso_calendar"

    # App
    app_name: str = "Economic Release Calendar"
    debug: bool = True

    # Scheduler
    scheduler_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="")


settings = Settings()
