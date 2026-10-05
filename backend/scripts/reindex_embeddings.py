#!/usr/bin/env python3
"""Regenerate all menu and restaurant-knowledge vectors for the configured Ollama model."""

import argparse
import asyncio
import logging
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_ollama import OllamaEmbeddings
from pymongo import AsyncMongoClient, UpdateOne

from app.core.config import settings
from app.evaluation.embedding_migration import (
    VECTOR_INDEX_NAME,
    get_vector_index_dimensions,
    vector_index_definition,
)
from app.service.menu import menu_embedding_text


logger = logging.getLogger(__name__)
INDEX_READY_TIMEOUT_SECONDS = 300


def _index_model(dimensions: int) -> dict[str, Any]:
    return {
        "name": VECTOR_INDEX_NAME,
        "type": "vectorSearch",
        "definition": vector_index_definition(dimensions),
    }


async def _ensure_vector_index(
    database: Any,
    collection_name: str,
    dimensions: int,
) -> None:
    collection = database[collection_name]
    indexes = await (await collection.list_search_indexes()).to_list(length=None)
    existing = next(
        (index for index in indexes if index.get("name") == VECTOR_INDEX_NAME),
        None,
    )
    if existing is not None and get_vector_index_dimensions(existing) != dimensions:
        await database.command(
            "dropSearchIndex",
            collection_name,
            name=VECTOR_INDEX_NAME,
        )
        existing = None
    if existing is None:
        await database.command(
            "createSearchIndexes",
            collection_name,
            indexes=[_index_model(dimensions)],
        )

    deadline = time.monotonic() + INDEX_READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        indexes = await (await collection.list_search_indexes()).to_list(length=None)
        current = next(
            (index for index in indexes if index.get("name") == VECTOR_INDEX_NAME),
            None,
        )
        if current is None:
            raise RuntimeError(
                f"MongoDB did not create vector index {VECTOR_INDEX_NAME!r} "
                f"on collection {collection_name!r}."
            )
        status = current.get("status")
        if status == "FAILED":
            raise RuntimeError(
                f"MongoDB vector index {VECTOR_INDEX_NAME!r} failed on "
                f"{collection_name!r}: {current.get('statusDetail', 'no details')}"
            )
        if (
            status == "READY"
            and current.get("queryable") is True
            and get_vector_index_dimensions(current) == dimensions
        ):
            return
        await asyncio.sleep(1)
    raise TimeoutError(
        f"MongoDB vector index {VECTOR_INDEX_NAME!r} on {collection_name!r} "
        f"did not become queryable within {INDEX_READY_TIMEOUT_SECONDS} seconds."
    )


def _embedding_text(collection_name: str, document: Mapping[str, Any]) -> str:
    if collection_name == "menu":
        return menu_embedding_text(document)
    content = document.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(
            f"Knowledge document {document.get('_id')!r} has no non-empty content."
        )
    return content


async def _prepare_collection_embeddings(
    database: Any,
    collection_name: str,
    embedding_model: OllamaEmbeddings,
    dimensions: int,
) -> tuple[list[dict[str, Any]], list[list[float]]]:
    collection = database[collection_name]
    documents = await collection.find({}).to_list(length=None)
    if not documents:
        logger.info("Collection %s is empty; no vectors to regenerate.", collection_name)
        return documents, []

    texts = [_embedding_text(collection_name, document) for document in documents]
    vectors = await embedding_model.aembed_documents(texts)
    if len(vectors) != len(documents):
        raise RuntimeError(
            f"Embedding model returned {len(vectors)} vectors for "
            f"{len(documents)} documents in {collection_name!r}."
        )
    invalid_dimensions = sorted(
        {len(vector) for vector in vectors if len(vector) != dimensions}
    )
    if invalid_dimensions:
        raise RuntimeError(
            f"Embedding model {settings.EMBEDDING_MODEL!r} returned dimensions "
            f"{invalid_dimensions}; configured index dimension is {dimensions}."
        )

    return documents, vectors


async def _migrate_collections(
    database: Any,
    collection_names: list[str],
    embedding_model: OllamaEmbeddings,
    dimensions: int,
) -> dict[str, int]:
    prepared_embeddings = {}
    for collection_name in collection_names:
        prepared_embeddings[collection_name] = await _prepare_collection_embeddings(
            database,
            collection_name,
            embedding_model,
            dimensions,
        )

    for collection_name in collection_names:
        await _ensure_vector_index(database, collection_name, dimensions)

    counts = {}
    for collection_name in collection_names:
        documents, vectors = prepared_embeddings[collection_name]
        counts[collection_name] = await _store_collection_embeddings(
            database,
            collection_name,
            documents,
            vectors,
            dimensions,
        )
    return counts


async def _store_collection_embeddings(
    database: Any,
    collection_name: str,
    documents: list[dict[str, Any]],
    vectors: list[list[float]],
    dimensions: int,
) -> int:
    if not documents:
        return 0
    collection = database[collection_name]
    operations = [
        UpdateOne(
            {"_id": document["_id"]},
            {"$set": {"embedding": vector}},
        )
        for document, vector in zip(documents, vectors)
    ]
    await collection.bulk_write(operations, ordered=True)

    stored_documents = await collection.find({}, {"embedding": 1}).to_list(length=None)
    invalid_stored = [
        document.get("_id")
        for document in stored_documents
        if not isinstance(document.get("embedding"), list)
        or len(document["embedding"]) != dimensions
    ]
    if invalid_stored:
        raise RuntimeError(
            f"Reindex verification failed for {len(invalid_stored)} documents "
            f"in {collection_name!r}."
        )
    logger.info("Reindexed and verified %d documents in %s.", len(documents), collection_name)
    return len(documents)


async def reindex_database() -> dict[str, int]:
    if settings.EMBEDDING_DIMENSIONS < 1:
        raise ValueError("EMBEDDING_DIMENSIONS must be greater than zero.")
    client = AsyncMongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
        database = client[settings.DB_NAME]
        collection_names = set(await database.list_collection_names())
        target_collections = ["menu"]
        if "knowledge" in collection_names:
            target_collections.append("knowledge")
        embedding_model = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )
        return await _migrate_collections(
            database,
            target_collections,
            embedding_model,
            settings.EMBEDDING_DIMENSIONS,
        )
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    counts = asyncio.run(reindex_database())
    print(
        "Embedding migration complete: "
        + ", ".join(f"{name}={count}" for name, count in counts.items())
    )


if __name__ == "__main__":
    main()
