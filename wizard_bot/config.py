from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WizardSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    WIZARD_BOT_TOKEN: str
    WIZARD_ADMIN_IDS: list[int]
    WIZARD_REDIS_URL: str = "redis://redis:6379/1"
    SOCIALBRIDGE_ADMIN_BASE_URL: str = "http://api:8000"
    SOCIALBRIDGE_ADMIN_TOKEN: str
    WIZARD_POLL_TIMEOUT_SECONDS: int = 20
    WIZARD_CAMPAIGNS_PAGE_LIMIT: int = 50

    @field_validator("WIZARD_ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | list[int]) -> list[int]:
        if isinstance(value, list):
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("WIZARD_ADMIN_IDS must be a comma-separated list")
        return [int(item.strip()) for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> WizardSettings:
    return WizardSettings()
