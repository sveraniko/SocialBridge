from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BASE_URL: str
    SIS_BOT_USERNAME: str
    DATABASE_URL: str
    ADMIN_TOKEN: str
    MC_TOKEN: str
    MC_TOKEN_REQUIRED: bool = True
    STORE_TEXT_PREVIEW: bool = False
    CLICK_LOG_IP: bool = False
    IP_HASH_SALT: str | None = None
    RETENTION_INBOUND_DAYS: int = 90
    RETENTION_CLICK_DAYS: int = 365
    DYNAMIC_MAPPING_MAX_PER_DAY: int = 500
    LOG_LEVEL: str = "INFO"

    @field_validator("IP_HASH_SALT")
    @classmethod
    def validate_ip_hash_salt(cls, value: str | None, info):
        if info.data.get("CLICK_LOG_IP") and not value:
            raise ValueError("IP_HASH_SALT is required when CLICK_LOG_IP=true")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
