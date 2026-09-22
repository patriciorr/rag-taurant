# app/rag/embeddings.py
from langchain_ollama import OllamaEmbeddings
from app.core.config import settings

# Instancia global configurada con el modelo y la URL de Ollama
embeddings_service = OllamaEmbeddings(
    model=settings.EMBEDDING_MODEL,
    base_url=settings.OLLAMA_BASE_URL
)

async def get_embedding(text: str) -> list[float]:
    """Obtiene el embedding de un único texto de forma asíncrona."""
    return await embeddings_service.aembed_query(text)

async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Obtiene embeddings para una lista de textos en lote de forma asíncrona."""
    return await embeddings_service.aembed_documents(texts)