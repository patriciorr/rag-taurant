from typing import Any, Mapping


VECTOR_INDEX_NAME = "vector_index"


def vector_index_definition(dimensions: int) -> dict[str, Any]:
    if dimensions < 1:
        raise ValueError("Embedding dimensions must be greater than zero.")
    return {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": dimensions,
                "similarity": "cosine",
            }
        ]
    }


def get_vector_index_dimensions(index: Mapping[str, Any]) -> int | None:
    definition = index.get("latestDefinition") or index.get("definition")
    if not isinstance(definition, Mapping):
        return None
    fields = definition.get("fields")
    if not isinstance(fields, list):
        return None
    for field in fields:
        if (
            isinstance(field, Mapping)
            and field.get("type") == "vector"
            and field.get("path") == "embedding"
        ):
            dimensions = field.get("numDimensions")
            return dimensions if isinstance(dimensions, int) else None
    return None
