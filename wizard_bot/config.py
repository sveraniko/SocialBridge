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
    WIZARD_DEFAULT_CHANNEL: str = "ig"
    WIZARD_PUBLIC_BASE_URL: str = "http://localhost:8000"
    WIZARD_SIS_BOT_USERNAME: str = ""
    WIZARD_MC_RESOLVE_URL: str = "https://your-domain.com/v1/mc/resolve"
    WIZARD_MC_TOKEN: str = "<YOUR_MC_TOKEN>"
    WIZARD_KEYWORD_PRODUCT: str = "BUY"
    WIZARD_KEYWORD_LOOK: str = "LOOK"
    WIZARD_KEYWORD_CATALOG: str = "CAT"
    WIZARD_KEYWORDS_PRODUCT: str = "BUY"
    WIZARD_KEYWORDS_LOOK: str = "LOOK"
    WIZARD_KEYWORDS_CATALOG: str = "CAT"
    WIZARD_LOOK_PREFIX: str = "LOOK_"
    WIZARD_RESOLVE_REQUIRE_KEYWORD: bool = False
    WIZARD_KEYWORD_CASE_SENSITIVE: bool = False

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
