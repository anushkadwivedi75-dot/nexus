from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Nexus API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & Cryptography Configuration
    # Minimum 256-bit secret key for HMAC-SHA256 JWT signing
    JWT_SECRET: str = "nexus_dev_super_secret_jwt_signing_key_at_least_32_bytes_long_12345"
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "nexus-api"
    JWT_AUDIENCE: str = "nexus-web"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 256-bit (32 bytes) hex-encoded key for AES-256-GCM grace stash encryption
    TOKEN_ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    # Cookie Specifications per Blueprint Section 6.1
    REFRESH_COOKIE_NAME_PROD: str = "__Host-nexus_rt"
    REFRESH_COOKIE_NAME_DEV: str = "nexus_rt_dev"

    # PostgreSQL Configuration
    POSTGRES_DB: str = "nexus_dev"
    POSTGRES_USER: str = "nexus_migrator"
    POSTGRES_PASSWORD: str = "migrator_dev_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "dev_redis_password"

    # Explicit Connection URLs (optional overrides)
    DATABASE_URL: str | None = None
    DATABASE_SYNC_URL: str | None = None
    REDIS_URL: str | None = None

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_SYNC_URL:
            return self.DATABASE_SYNC_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_connection_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def refresh_cookie_name(self) -> str:
        return self.REFRESH_COOKIE_NAME_PROD if self.APP_ENV == "production" else self.REFRESH_COOKIE_NAME_DEV

    @property
    def refresh_cookie_secure(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
