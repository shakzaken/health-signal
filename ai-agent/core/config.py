from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    anthropic_api_key: str
    openai_api_key: str
    langsmith_api_key: str = ""
    langsmith_project: str = "health-signal"
    langchain_tracing_v2: str = "true"


settings = Settings()
