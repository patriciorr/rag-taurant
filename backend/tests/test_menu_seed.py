from copy import deepcopy

import pytest

from app.core import init_db


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    async def to_list(self, length=None):
        return deepcopy(self.documents)


class FakeCollection:
    def __init__(self):
        self.documents = [{"id": "custom-dish", "name": "Do not delete this"}]
        self.updates = []

    def find(self, query):
        requested_ids = set(query["id"]["$in"])
        return FakeCursor([item for item in self.documents if item.get("id") in requested_ids])

    async def update_one(self, query, update, upsert):
        self.updates.append((query, update, upsert))
        item = next(
            (item for item in self.documents if item.get("id") == query["id"]),
            None,
        )
        if item is None:
            item = {"id": query["id"]}
            self.documents.append(item)
        item.update(update["$set"])


class FakeDatabase:
    def __init__(self):
        self.collection = FakeCollection()

    def __getitem__(self, name):
        assert name == "menu"
        return self.collection


@pytest.mark.asyncio
async def test_seed_upserts_catalog_without_deleting_custom_menu_data(monkeypatch):
    database = FakeDatabase()
    monkeypatch.setattr(init_db.db_instance, "db", database)
    embedding_calls = []

    async def get_embeddings_batch(texts):
        embedding_calls.append(texts)
        return [[float(index)] for index, _ in enumerate(texts)]

    monkeypatch.setattr(init_db, "get_embeddings_batch", get_embeddings_batch)

    await init_db.seed_initial_menu()

    seeded_ids = {item["id"] for item in init_db.INITIAL_MENU}
    stored_ids = {item["id"] for item in database.collection.documents}
    assert seeded_ids <= stored_ids
    assert "custom-dish" in stored_ids
    assert len(embedding_calls) == 1
    assert len(embedding_calls[0]) == len(init_db.INITIAL_MENU)
    assert all(
        item["image_url"] is None or item["image_url"].startswith("/assets/menu/")
        for item in database.collection.documents
        if item["id"] in seeded_ids
    )
    assert all(
        item["embedding_model"] == init_db.settings.EMBEDDING_MODEL
        and item["embedding_dimensions"] == init_db.settings.EMBEDDING_DIMENSIONS
        for item in database.collection.documents
        if item["id"] in seeded_ids
    )

    await init_db.seed_initial_menu()

    assert len(embedding_calls) == 1
    assert len(database.collection.updates) == len(init_db.INITIAL_MENU)


def test_curated_menu_images_and_allergens_match_public_api_contract():
    from app.models.menu import Allergen, MenuItem

    seeded_items = [MenuItem(**item) for item in init_db.INITIAL_MENU]
    covered_allergens = {allergen.value for item in seeded_items for allergen in item.allergens}

    assert {allergen.value for allergen in Allergen} <= covered_allergens
    assert all(item.image_url for item in seeded_items)
    drinks = [item for item in seeded_items if item.category.value == "bebida"]
    assert len(drinks) == 7
    assert {item.id for item in drinks} == {str(number) for number in range(13, 20)}
    assert len({item.id for item in seeded_items}) == len(seeded_items)
    by_name = {item.name: item for item in drinks}
    assert by_name["Vino blanco"].allergens == [Allergen.SULFITOS]
    assert "pescados" in by_name["Vino blanco"].description
    assert by_name["Vino tinto"].allergens == [Allergen.SULFITOS]
    assert "carnes" in by_name["Vino tinto"].description
    assert by_name["Cerveza"].allergens == [Allergen.GLUTEN]
    assert Allergen.GLUTEN not in by_name["Cerveza artesanal sin gluten"].allergens
    assert any(item.is_vegan for item in seeded_items)
    assert any(item.is_vegetarian and not item.is_vegan for item in seeded_items)
