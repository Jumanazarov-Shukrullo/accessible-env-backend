from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    database_url: str = Field(...)
    pool_size: int = Field(...)


class AuthSettings(BaseSettings):
    secret_key: str = Field(...)
    algorithm: str = Field("HS256")
    access_token_expires: int = Field(120)

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    frontend_base_url: str


class StorageSettings(BaseSettings):
    minio_endpoint: str = Field("minio:9000")
    minio_access_key: str = Field(...)
    minio_secret_key: str = Field(...)
    minio_bucket: str = Field(...)
    minio_use_ssl: bool = Field(True)  # Use HTTPS by default for production


class CacheSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    ttl_seconds: int = 3600  # Default 1 hour for relatively static data
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    redis_retry_on_timeout: bool = True


class MessagingSettings(BaseSettings):
    kafka_bootstrap_servers: List[str] = Field(default_factory=list)
    rabbitmq_url: str = Field("amqp://rabbitmq:5672")

    @classmethod
    def _split_servers(cls, v: str) -> List[str]:
        return [server.strip() for server in v.split(",") if server.strip()]

    @field_validator("kafka_bootstrap_servers", mode="before")
    @classmethod
    def validate_kafka_bootstrap_servers(cls, v: str) -> List[str]:
        return cls._split_servers(v) if isinstance(v, str) else v


class SMTPSettings(BaseSettings):
    smtp_server: str = Field("smtp.gmail.com")
    smtp_port: int = Field(587)
    sender_email: str = Field(...)
    sender_password: str = Field(...)


class AppSettings(BaseSettings):
    debug: bool = Field(False)
    allowed_hosts: List[str] = Field(default_factory=list)
    session_secret_key: str = Field(...)
    backend_url: str = Field(...)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    messaging: MessagingSettings = Field(default_factory=MessagingSettings)
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    cache: CacheSettings = CacheSettings()

    @classmethod
    def _split_allowed_hosts(cls, v: str) -> List[str]:
        return [host.strip() for host in v.split(",") if host.strip()]

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def split_allowed_hosts(cls, v):
        if isinstance(v, str):
            return cls._split_allowed_hosts(v)
        return v

    class Config:
        env_prefix = "APP_"
        case_sensitive = False
        env_nested_delimiter = "__"
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


settings: AppSettings = AppSettings()

if __name__ == "__main__":
    settings = AppSettings()
    print(settings.model_dump())
