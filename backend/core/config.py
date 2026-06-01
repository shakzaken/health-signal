from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    ai_agent_url: str = "http://localhost:8001"
    file_storage_path: str = "./uploads"


settings = Settings()
