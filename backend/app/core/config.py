# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Gourmet RAG Restaurant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
        
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIMENSIONS: int = 1024
    
    OLLAMA_BASE_URL: str = "http://localhost:11435"
    OLLAMA_MODEL: str = "qwen3:8b"
    
    RESTAURANT_LAT: float = 37.3891
    RESTAURANT_LON: float = -5.9845

    MONGODB_URI: str = "mongodb://localhost:27017/?directConnection=true"
    DB_NAME: str = "rag_taurant"

    class Config:
        env_file = ".env"

settings = Settings()