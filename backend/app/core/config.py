from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # 所有可通过 .env 覆盖的运行参数都集中在这里。
    app_name: str = "Yield Ledger"
    api_prefix: str = "/api"
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'dividend_tracker.db'}"
    data_dir: str = str(ROOT_DIR / "data")
    timezone: str = "Asia/Shanghai"
    scheduler_enabled: bool = True
    holdings_refresh_minutes: int = 30
    holdings_daily_refresh_hour: int = 3
    holdings_daily_refresh_minute: int = 0
    base_currency: str = "CNY"
    usd_to_cny: float = 7.20
    hkd_to_cny: float = 0.92
    sync_timeout_seconds: int = 20
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    # 配置对象全局复用，避免反复读取环境变量。
    return Settings()
