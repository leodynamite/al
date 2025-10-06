from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


load_dotenv()


class TelegramConfig(BaseModel):
    bot_token: str = Field(min_length=10)


class LLMConfig(BaseModel):
    base_url: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    api_key: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", "")))
    model: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))


class StorageConfig(BaseModel):
    data_dir: Path = Field(default=Path(os.getenv("ALBOT_DATA_DIR", "./data")))


class AppConfig(BaseModel):
    telegram: TelegramConfig
    llm: LLMConfig = Field(default_factory=LLMConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    # WebApp (Mini App)
    webapp_url: str | None = Field(default_factory=lambda: os.getenv("WEBAPP_URL"))
    # Telegram channels
    telegram_managers_channel_id: str | None = Field(default_factory=lambda: os.getenv("TELEGRAM_HOT_LEADS_CHANNEL_ID"))
    telegram_errors_channel_id: str | None = Field(default_factory=lambda: os.getenv("TELEGRAM_ERRORS_CHANNEL_ID"))
    # Email
    smtp_host: str | None = Field(default_factory=lambda: os.getenv("SMTP_HOST"))
    smtp_port: int | None = Field(default_factory=lambda: int(os.getenv("SMTP_PORT", "0")) if os.getenv("SMTP_PORT") else None)
    smtp_user: str | None = Field(default_factory=lambda: os.getenv("SMTP_USER"))
    smtp_password: str | None = Field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    # Yandex OAuth
    yandex_client_id: str | None = Field(default_factory=lambda: os.getenv("YANDEX_CLIENT_ID"))
    yandex_client_secret: str | None = Field(default_factory=lambda: os.getenv("YANDEX_CLIENT_SECRET"))
    yandex_redirect_uri: str | None = Field(default_factory=lambda: os.getenv("YANDEX_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob"))
    yandex_auth_url: str = Field(default_factory=lambda: os.getenv("YANDEX_AUTH_URL", "https://oauth.yandex.ru/authorize"))
    yandex_token_url: str = Field(default_factory=lambda: os.getenv("YANDEX_TOKEN_URL", "https://oauth.yandex.ru/token"))
    yandex_calendar_api_base: str = Field(default_factory=lambda: os.getenv("YANDEX_CAL_API_BASE", "https://api.calendar.yandex.net"))
    # Supabase & encryption
    supabase_url: str | None = Field(default_factory=lambda: os.getenv("SUPABASE_URL"))
    supabase_anon_key: str | None = Field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY"))
    encryption_key: str | None = Field(default_factory=lambda: os.getenv("ENCRYPTION_KEY"))
    # Billing
    trial_days: int = Field(default=14)
    trial_dialogs: int = Field(default=50)
    yo_money_shop_id: str | None = Field(default_factory=lambda: os.getenv("YO_MONEY_SHOP_ID"))
    yo_money_secret: str | None = Field(default_factory=lambda: os.getenv("YO_MONEY_SECRET"))
    # Monitoring
    errors_channel_id: str | None = Field(default_factory=lambda: os.getenv("TELEGRAM_ERRORS_CHANNEL_ID"))
    sentry_dsn: str | None = Field(default_factory=lambda: os.getenv("SENTRY_DSN"))

    @staticmethod
    def load() -> "AppConfig":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        config = AppConfig(telegram=TelegramConfig(bot_token=token))
        config.storage.data_dir.mkdir(parents=True, exist_ok=True)
        return config


