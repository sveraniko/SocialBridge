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
    KEYWORD_PRODUCT: str = "BUY"
    KEYWORD_LOOK: str = "LOOK"
    KEYWORD_CATALOG: str = "CAT"
    KEYWORDS_PRODUCT: str = "BUY"
    KEYWORDS_LOOK: str = "LOOK"
    KEYWORDS_CATALOG: str = "CAT"
    KEYWORD_CASE_SENSITIVE: bool = False
    LOOK_PREFIX: str = "LOOK_"
    RESOLVE_ALLOW_CODE_ONLY: bool = True
    RESOLVE_REQUIRE_KEYWORD: bool = False
    RESOLVE_AMBIGUOUS_POLICY: str = "prefer_product"

    @field_validator("IP_HASH_SALT")
    @classmethod
    def validate_ip_hash_salt(cls, value: str | None, info):
        if info.data.get("CLICK_LOG_IP") and not value:
            raise ValueError("IP_HASH_SALT is required when CLICK_LOG_IP=true")
        return value

    @property
    def keyword_product_list(self) -> list[str]:
        return self._csv_keywords(self.KEYWORDS_PRODUCT or self.KEYWORD_PRODUCT, self.KEYWORD_PRODUCT)

    @property
    def keyword_look_list(self) -> list[str]:
        return self._csv_keywords(self.KEYWORDS_LOOK or self.KEYWORD_LOOK, self.KEYWORD_LOOK)

    @property
    def keyword_catalog_list(self) -> list[str]:
        return self._csv_keywords(self.KEYWORDS_CATALOG or self.KEYWORD_CATALOG, self.KEYWORD_CATALOG)

    @staticmethod
    def _csv_keywords(raw: str, fallback: str) -> list[str]:
        values = [item.strip() for item in raw.split(",") if item.strip()]
        return values or [fallback]

    @field_validator("RESOLVE_AMBIGUOUS_POLICY")
    @classmethod
    def validate_ambiguous_policy(cls, value: str) -> str:
        allowed = {"prefer_product", "prefer_look", "ask"}
        if value not in allowed:
            raise ValueError(f"RESOLVE_AMBIGUOUS_POLICY must be one of {sorted(allowed)}")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
