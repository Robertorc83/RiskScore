"""Configuration management using Pydantic Settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/gerald"

    # External Services
    bank_api_base: str = "http://localhost:8001"
    ledger_webhook_url: str = "http://localhost:8002/mock-ledger"

    # Service
    service_name: str = "gerald-gateway"
    log_level: str = "INFO"

    # HTTP Client
    http_timeout_seconds: float = 5.0
    webhook_max_retries: int = 5
    webhook_backoff_base: float = 1.0  # Exponential backoff base in seconds


settings = Settings()
