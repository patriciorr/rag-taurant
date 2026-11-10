# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Gourmet RAG Restaurant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
        
    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL: str = "gemini-3.5-flash-lite"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSIONS: int = 768
    
    RESTAURANT_LAT: float = 37.3167
    RESTAURANT_LON: float = -6.8414

    MONGODB_URI: str = "mongodb://localhost:27017/?directConnection=true"
    DB_NAME: str = "rag_taurant"

    class Config:
        env_file = ".env"

settings = Settings()