from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    secret_key: str
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    openai_api_key: str
    openai_model: str = "gpt-4.1-nano"
    openrouter_api_key: str
    embedding_model: str = "qwen/qwen3-embedding-8b"
    backend_url: str = "http://localhost:8000"
    langsmith_api_key: str = ""
    langsmith_project: str = "health-signal"
    langchain_tracing_v2: str = "true"


settings = Settings()
