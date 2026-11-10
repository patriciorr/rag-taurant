import pytest

from app.evaluation.embedding_migration import get_vector_index_dimensions, vector_index_definition
from app.service.menu import menu_embedding_text
from scripts import reindex_embeddings


def test_vector_index_definition_uses_configured_embedding_dimensions():
    assert vector_index_definition(1024) == {
        "fields": [{
            "type": "vector",
            "path": "embedding",
            "numDimensions": 1024,
            "similarity": "cosine",
        }]
    }


@pytest.mark.parametrize("key", ["definition", "latestDefinition"])
def test_vector_index_dimensions_reads_index_shapes(key):
    assert get_vector_index_dimensions({
        key: {"fields": [{"type": "vector", "path": "embedding", "numDimensions": 768}]}
    }) == 768
    assert get_vector_index_dimensions({key: {"fields": []}}) is None


def test_menu_embedding_text_includes_structured_diet_and_allergens():
    text = menu_embedding_text({
        "name": "Gazpacho",
        "category": "entrante",
        "price": 8.5,
        "description": "Sopa fría",
        "is_vegan": True,
        "is_vegetarian": True,
        "allergens": [],
    })
    assert "Plato: Gazpacho" in text
    assert "Apto para veganos: Sí" in text
    assert "Alérgenos: Ninguno" in text


@pytest.mark.asyncio
async def test_reindex_prepares_every_collection_before_modifying_indexes(monkeypatch):
    operations = []

    async def prepare(database, collection_name, embedding_model, dimensions):
        operations.append(("prepare", collection_name))
        if collection_name == "knowledge":
            raise RuntimeError("Embedding request failed.")
        return ([{"_id": "menu-1"}], [[0.1] * dimensions])

    async def ensure_index(database, collection_name, dimensions):
        operations.append(("index", collection_name))

    async def store(database, collection_name, documents, vectors, dimensions):
        operations.append(("store", collection_name))
        return len(documents)

    monkeypatch.setattr(reindex_embeddings, "_prepare_collection_embeddings", prepare)
    monkeypatch.setattr(reindex_embeddings, "_ensure_vector_index", ensure_index)
    monkeypatch.setattr(reindex_embeddings, "_store_collection_embeddings", store)
    with pytest.raises(RuntimeError, match="Embedding request failed"):
        await reindex_embeddings._migrate_collections(
            database=object(), collection_names=["menu", "knowledge"],
            embedding_model=object(), dimensions=1024,
        )
    assert operations == [("prepare", "menu"), ("prepare", "knowledge")]
