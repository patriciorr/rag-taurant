import math

from app.core.config import settings
from app.core.database import db_instance
from app.evaluation.embedding_migration import VECTOR_INDEX_NAME

_EXCLUDED_FIELDS = {"_id": 0, "embedding": 0, "embedding_model": 0, "embedding_dimensions": 0}


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


async def vector_search(collection_name: str, query_vector: list[float], limit: int) -> list[dict]:
    """Returns the closest documents, using Atlas $vectorSearch or an in-process ranking."""
    collection = db_instance.db[collection_name]
    if settings.VECTOR_SEARCH_MODE == "atlas":
        pipeline = [
            {
                "$vectorSearch": {
                    "index": VECTOR_INDEX_NAME,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit,
                }
            },
            {"$project": {**_EXCLUDED_FIELDS, "score": {"$meta": "vectorSearchScore"}}},
        ]
        cursor = await collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    documents = await collection.find({"embedding": {"$type": "array"}}, {"_id": 0}).to_list(
        length=None
    )
    scored = [(_cosine_similarity(query_vector, doc["embedding"]), doc) for doc in documents]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = []
    for score, doc in scored[:limit]:
        result = {k: v for k, v in doc.items() if k not in _EXCLUDED_FIELDS}
        result["score"] = score
        results.append(result)
    return results
