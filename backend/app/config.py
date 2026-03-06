from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:////app/data/rss_reader.db"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3.5:9b"
    rsshub_base_url: str = "http://rsshub:1200"
    digest_time: str = "07:00"  # HH:MM
    fetch_interval: int = 3600  # seconds

    model_config = {"env_file": ".env"}


settings = Settings()
