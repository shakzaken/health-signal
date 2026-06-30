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
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    openai_api_key: str
    openai_model: str = "gpt-4.1-nano"
    openrouter_api_key: str
    embedding_model: str = "qwen/qwen3-embedding-8b"
    backend_url: str = "http://localhost:8000"
    langsmith_api_key: str = ""
    langsmith_project: str = "health-signal"
    langchain_tracing_v2: str = "true"
    sentry_dsn: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
