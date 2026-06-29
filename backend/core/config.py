from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    secret_key: str
    ai_agent_url: str = "http://localhost:8001"
    file_storage_path: str = "./uploads"
    environment: str = "production"
    resend_api_key: str = ""
    frontend_url: str = "https://healthsignal.yakirzaken.com"
    sentry_dsn: str = ""


settings = Settings()
