# app/rag/embeddings.py
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

embeddings_service = GoogleGenerativeAIEmbeddings(
    model=settings.EMBEDDING_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    output_dimensionality=settings.EMBEDDING_DIMENSIONS,
)


def _validate_vector(vector: list[float]) -> list[float]:
    if len(vector) != settings.EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Embedding model returned {len(vector)} dimensions; "
            f"expected {settings.EMBEDDING_DIMENSIONS}."
        )
    return vector


async def get_embedding(text: str) -> list[float]:
    """Obtiene el embedding de un único texto de forma asíncrona."""
    return _validate_vector(await embeddings_service.aembed_query(text))

async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Obtiene embeddings para una lista de textos en lote de forma asíncrona."""
    vectors = await embeddings_service.aembed_documents(texts)
    if len(vectors) != len(texts):
        raise ValueError(
            f"Embedding model returned {len(vectors)} vectors for {len(texts)} documents."
        )
    return [_validate_vector(vector) for vector in vectors]