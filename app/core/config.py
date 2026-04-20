from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "super-secret-key"

    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/payments_db"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    payments_exchange: str = "payments"
    payments_queue: str = "payments.new"
    payments_dlq: str = "payments.dlq"


settings = Settings()
