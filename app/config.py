from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- Supabase ---
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str

    # --- Database (asyncpg via PgBouncer port 6543) ---
    DATABASE_URL: str

    # --- Razorpay ---
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str

    # --- SMS & Email ---
    MSG91_API_KEY: str
    RESEND_API_KEY: str

    # --- App ---
    ENVIRONMENT: str = "local"          # local | staging | production
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Optional ---
    SENTRY_DSN: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
