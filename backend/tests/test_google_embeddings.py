from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.rag import embeddings


@pytest.mark.asyncio
async def test_google_embeddings_use_query_and_document_tasks(monkeypatch):
    vector = [0.1] * embeddings.settings.EMBEDDING_DIMENSIONS
    embed_content = AsyncMock(
        return_value=SimpleNamespace(embeddings=[SimpleNamespace(values=vector)])
    )
    client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content))
    )
    monkeypatch.setattr(embeddings.embeddings_service, "client", client)

    assert await embeddings.get_embedding("gazpacho") == vector
    query_call = embed_content.await_args.kwargs
    assert query_call["config"].task_type == "RETRIEVAL_QUERY"
    assert query_call["config"].output_dimensionality == embeddings.settings.EMBEDDING_DIMENSIONS

    assert await embeddings.get_embeddings_batch(["Gazpacho frío"]) == [vector]
    document_call = embed_content.await_args.kwargs
    assert document_call["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert document_call["config"].output_dimensionality == embeddings.settings.EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_embeddings_reject_invalid_count_and_dimensions(monkeypatch):
    service = SimpleNamespace(
        aembed_documents=AsyncMock(return_value=[]),
        aembed_query=AsyncMock(return_value=[0.1]),
    )
    monkeypatch.setattr(embeddings, "embeddings_service", service)
    with pytest.raises(ValueError, match="0 vectors for 1 documents"):
        await embeddings.get_embeddings_batch(["Gazpacho"])

    with pytest.raises(ValueError, match="1 dimensions"):
        await embeddings.get_embedding("Gazpacho")
