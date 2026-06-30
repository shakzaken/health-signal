from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "adminuser"
    postgres_password: str
    postgres_db: str = "healthsignal"
    secret_key: str
    ai_agent_url: str = "http://localhost:8001"
    file_storage_path: str = "./uploads"
    environment: str = "production"
    resend_api_key: str = ""
    frontend_url: str = "https://healthsignal.yakirzaken.com"
    sentry_dsn: str = ""
    google_client_id: str = ""
    admin_email: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
