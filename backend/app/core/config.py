from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JobFlow API"
    app_env: str = "dev"
    database_url: str
    secret_key: str

    # Job sources, comma-separated in priority order. Greenhouse is the
    # default because it returns real listings without any credentials.
    # "seed" is synthetic sample data — opt in only for offline development.
    job_sources: str = "greenhouse"
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    greenhouse_boards: str | None = None

    # LLM (Groq). Without a key the AI endpoints return 503 rather than failing
    # the whole app at import time.
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    # Used in alert messages so recipients get a working link.
    frontend_url: str = "http://localhost:5173"

    # --- Notifications ---------------------------------------------------
    # WhatsApp via Meta's Cloud API. Business-initiated messages must use an
    # approved template, hence the template name and language.
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_template_name: str | None = None
    whatsapp_template_language: str = "en"

    # With no channel configured, log alerts instead of dropping them so the
    # pipeline can be exercised in development.
    notifications_fallback_to_console: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
