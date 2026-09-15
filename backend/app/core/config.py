# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Gourmet RAG Restaurant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    MENU_DATA_PATH: str = "./data/menu.json"
    RESERVATIONS_DATA_PATH: str = "./data/reservations.json"
    
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Ollama en Docker
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"
    
    # Coordenadas por defecto para el tiempo (Ej. Sevilla)
    RESTAURANT_LAT: float = 37.3891
    RESTAURANT_LON: float = -5.9845

    class Config:
        env_file = ".env"

settings = Settings()