from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    service_name = "investment-data-api"
    version = "1.0.0"

    def __init__(self) -> None:
        self.app_api_token = os.getenv("APP_API_TOKEN", "")
        self.fmp_api_key = os.getenv("FMP_API_KEY", "")
        self.tushare_token = os.getenv("TUSHARE_TOKEN", "")
        self.sec_user_agent = os.getenv("SEC_USER_AGENT", "")
        self.http_timeout_seconds = float(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "300"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

