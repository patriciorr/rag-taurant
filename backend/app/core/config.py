from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Gourmet RAG Restaurant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "production"] = "development"

    GOOGLE_API_KEY: str = ""
    MENU_ADMIN_TOKEN: str = ""
    GOOGLE_MODEL: str = "gemini-3.5-flash-lite"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSIONS: int = 768

    RESTAURANT_LAT: float = 37.3167
    RESTAURANT_LON: float = -6.8414

    MONGODB_URI: str = "mongodb://localhost:27017/?directConnection=true"
    DB_NAME: str = "rag_taurant"
    # "atlas" uses $vectorSearch; "local" ranks embeddings in Python for plain MongoDB.
    VECTOR_SEARCH_MODE: Literal["atlas", "local"] = "atlas"

    # Menu images live in an S3-compatible bucket (LocalStack locally, Railway Bucket in prod).
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = "ragtaurant-assets"
    S3_REGION: str = "us-east-1"
    # LocalStack needs "path"; Railway Buckets use "virtual" (older ones may still need "path").
    S3_ADDRESSING_STYLE: Literal["path", "virtual"] = "path"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""

    CORS_ORIGINS: str = "http://localhost,http://localhost:5173,http://127.0.0.1:5173"

    CHAT_MAX_MESSAGE_CHARS: int = 500
    CHAT_RATE_LIMIT_PER_MINUTE: int = 10
    CHAT_RATE_LIMIT_PER_DAY: int = 100
    CHAT_GLOBAL_DAILY_LIMIT: int = 500
    # Number of reverse proxies in front of the API whose X-Forwarded-For entry is trusted.
    TRUSTED_PROXY_COUNT: int = 1

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def require_secrets_in_production(self):
        if self.is_production:
            missing = [
                name
                for name in ("GOOGLE_API_KEY", "MENU_ADMIN_TOKEN")
                if not getattr(self, name).strip()
            ]
            if missing:
                raise ValueError(f"Missing required production settings: {', '.join(missing)}")
        return self


settings = Settings()
