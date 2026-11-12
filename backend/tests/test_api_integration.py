from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core import init_db
from app.repository.reservation import reservation_repository
from app.service import menu as menu_module
from scripts import reindex_embeddings

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_restaurant_information_seed_preserves_existing_knowledge(
    mongo_api_client, monkeypatch
):
    collection = init_db.db_instance.db["knowledge"]
    await collection.insert_one({"_id": "custom", "content": "Información personalizada."})
    calls = []

    async def embed(texts):
        calls.append(texts)
        return [[0.1] * init_db.settings.EMBEDDING_DIMENSIONS for _ in texts]

    monkeypatch.setattr(init_db, "get_embeddings_batch", embed)
    await init_db.seed_restaurant_information()
    await init_db.seed_restaurant_information()

    assert len(calls) == 1
    assert await collection.find_one({"_id": "custom"})
    stored = await collection.find_one({"_id": "curated:town"})
    assert stored["content"] == init_db.RESTAURANT_INFORMATION[2]["content"]
    assert stored["embedding_model"] == init_db.settings.EMBEDDING_MODEL
    response = await mongo_api_client.get("/api/v1/information/")
    assert response.status_code == 200
    assert any(item["content"] == stored["content"] for item in response.json())


@pytest.mark.asyncio
async def test_migration_preserves_documents_and_rejects_mixed_models(
    mongo_api_client, monkeypatch
):
    database = init_db.db_instance.db
    await database["menu"].insert_one(
        {"id": "custom", "name": "Gazpacho", "embedding": [0.1] * 768}
    )
    await database["knowledge"].insert_one(
        {"content": "La terraza abre de día.", "embedding": [0.2] * 768}
    )

    with pytest.raises(RuntimeError, match="unknown or incompatible"):
        await init_db.validate_embedding_models()

    class FakeEmbeddings:
        async def aembed_documents(self, texts):
            return [[0.3] * init_db.settings.EMBEDDING_DIMENSIONS for _ in texts]

    async def ensure_index(database, collection_name, dimensions):
        pass

    monkeypatch.setattr(reindex_embeddings, "_ensure_vector_index", ensure_index)
    counts = await reindex_embeddings._migrate_collections(
        database, ["menu", "knowledge"], FakeEmbeddings(), init_db.settings.EMBEDDING_DIMENSIONS
    )

    assert counts == {"menu": 1, "knowledge": 1}
    menu = await database["menu"].find_one({"id": "custom"})
    knowledge = await database["knowledge"].find_one({})
    assert menu["name"] == "Gazpacho"
    assert knowledge["content"] == "La terraza abre de día."
    assert menu["embedding_model"] == init_db.settings.EMBEDDING_MODEL
    assert knowledge["embedding_model"] == init_db.settings.EMBEDDING_MODEL
    await init_db.validate_embedding_models()

    await database["knowledge"].update_one({}, {"$set": {"embedding_model": "old-model"}})
    with pytest.raises(RuntimeError, match="unknown or incompatible"):
        await init_db.validate_embedding_models()


@pytest.fixture
def menu_embedding(monkeypatch):
    async def get_embedding(text):
        return [0.125, 0.25, 0.5]

    monkeypatch.setattr(menu_module, "get_embedding", get_embedding)

    async def get_embeddings_batch(texts):
        return [[0.125, 0.25, 0.5] for _ in texts]

    monkeypatch.setattr(menu_module, "get_embeddings_batch", get_embeddings_batch)


@pytest.mark.asyncio
async def test_menu_crud_uses_real_mongo_and_stubbed_embeddings(
    mongo_api_client, menu_embedding, monkeypatch
):
    monkeypatch.setattr(init_db.settings, "MENU_ADMIN_TOKEN", "test-menu-token")
    mongo_api_client.headers["Authorization"] = "Bearer test-menu-token"
    payload = {
        "name": "Gazpacho",
        "description": "Cold tomato soup",
        "price": 8.5,
        "category": "entrante",
        "allergens": [],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
    }

    created_response = await mongo_api_client.post("/api/v1/menu/", json=payload)

    assert created_response.status_code == 201
    dish_id = created_response.json()["id"]

    unchanged_response = await mongo_api_client.put(
        f"/api/v1/menu/{dish_id}",
        json=payload,
    )
    assert unchanged_response.status_code == 200

    listed_response = await mongo_api_client.get("/api/v1/menu/")
    assert [item["id"] for item in listed_response.json()] == [dish_id]

    patched_response = await mongo_api_client.patch(
        f"/api/v1/menu/{dish_id}",
        json={"price": 9.5},
    )
    assert patched_response.status_code == 200
    assert patched_response.json()["price"] == 9.5

    replacement = {**payload, "name": "Gazpacho de la casa", "price": 10.0}
    replaced_response = await mongo_api_client.put(
        f"/api/v1/menu/{dish_id}",
        json=replacement,
    )
    assert replaced_response.status_code == 200
    assert replaced_response.json()["name"] == "Gazpacho de la casa"

    deleted_response = await mongo_api_client.delete(f"/api/v1/menu/{dish_id}")
    assert deleted_response.status_code == 204
    assert (await mongo_api_client.get(f"/api/v1/menu/{dish_id}")).status_code == 404


@pytest.mark.asyncio
async def test_curated_menu_seed_is_idempotent_and_preserves_custom_documents(
    mongo_api_client,
    monkeypatch,
):
    collection = init_db.db_instance.db["menu"]
    await collection.insert_one({"id": "custom-dish", "name": "Keep this menu item"})
    embedding_calls = []

    async def get_embeddings_batch(texts):
        embedding_calls.append(texts)
        return [[float(index)] for index, _ in enumerate(texts)]

    monkeypatch.setattr(init_db, "get_embeddings_batch", get_embeddings_batch)

    await init_db.seed_initial_menu()

    first_count = await collection.count_documents({})
    assert first_count == len(init_db.INITIAL_MENU) + 1
    assert await collection.find_one({"id": "custom-dish"})
    assert len(embedding_calls) == 1

    await init_db.seed_initial_menu()

    assert await collection.count_documents({}) == first_count
    assert len(embedding_calls) == 1
    seeded_document = await collection.find_one({"id": "1"})
    assert seeded_document["image_url"] == "/assets/menu/gazpacho.jpg"


@pytest.mark.asyncio
async def test_reservations_enforce_contact_uniqueness_and_protected_crud(mongo_api_client):
    first_day = (datetime.now(ZoneInfo("Europe/Madrid")).date() + timedelta(days=2)).isoformat()

    def reservation_payload(email, phone, date):
        return {
            "customer_name": "Ana Perez",
            "email": email,
            "phone": phone,
            "date": date,
            "time": "18:30",
            "guests": 2,
        }

    first_response = await mongo_api_client.post(
        "/api/v1/reservations/",
        json=reservation_payload("ana@example.com", "612 345 678", first_day),
    )
    assert first_response.status_code == 201
    reservation_id = first_response.json()["reservation_id"]

    same_email = await mongo_api_client.post(
        "/api/v1/reservations/",
        json=reservation_payload("ANA@example.com", "+34 613 456 789", first_day),
    )
    assert same_email.status_code == 409
    assert same_email.json()["code"] == "RESERVATION_CONFLICT"

    same_phone = await mongo_api_client.post(
        "/api/v1/reservations/",
        json=reservation_payload("other@example.com", "+34 612 345 678", first_day),
    )
    assert same_phone.status_code == 409

    next_day = (datetime.now(ZoneInfo("Europe/Madrid")).date() + timedelta(days=3)).isoformat()
    another_day = await mongo_api_client.post(
        "/api/v1/reservations/",
        json=reservation_payload("ana@example.com", "612 345 678", next_day),
    )
    assert another_day.status_code == 201

    owner_headers = {
        "X-Reservation-Email": "ANA@example.com",
        "X-Reservation-Phone": "612 345 678",
    }
    read_response = await mongo_api_client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers=owner_headers,
    )
    assert read_response.status_code == 200

    changed_guests = await mongo_api_client.patch(
        f"/api/v1/reservations/{reservation_id}",
        headers=owner_headers,
        json={"guests": 4},
    )
    assert changed_guests.status_code == 200
    assert changed_guests.json()["guests"] == 4

    conflicting_move = await mongo_api_client.put(
        f"/api/v1/reservations/{another_day.json()['reservation_id']}",
        headers=owner_headers,
        json={"date": first_day, "time": "19:00", "guests": 2},
    )
    assert conflicting_move.status_code == 409

    replacement = await mongo_api_client.put(
        f"/api/v1/reservations/{reservation_id}",
        headers=owner_headers,
        json={"date": first_day, "time": "19:00", "guests": 3},
    )
    assert replacement.status_code == 200
    assert replacement.json()["time"] == "19:00"
    assert replacement.json()["guests"] == 3

    wrong_owner = await mongo_api_client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers={**owner_headers, "X-Reservation-Phone": "+34 600 000 000"},
    )
    assert wrong_owner.status_code == 404
    assert wrong_owner.json()["detail"] == "Reservation not found."

    cancelled = await mongo_api_client.delete(
        f"/api/v1/reservations/{reservation_id}",
        headers=owner_headers,
    )
    assert cancelled.status_code == 204

    retained = await mongo_api_client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers=owner_headers,
    )
    assert retained.status_code == 200
    assert retained.json()["status"] == "cancelled"

    repeated_cancellation = await mongo_api_client.delete(
        f"/api/v1/reservations/{reservation_id}",
        headers=owner_headers,
    )
    assert repeated_cancellation.status_code == 204

    rebooked = await mongo_api_client.post(
        "/api/v1/reservations/",
        json=reservation_payload("ana@example.com", "612 345 678", first_day),
    )
    assert rebooked.status_code == 201
    assert rebooked.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_ensure_indexes_upgrades_legacy_unconditional_unique_indexes(mongo_api_client):
    from app.core.database import db_instance

    collection = db_instance.db["reservations"]
    await collection.drop_indexes()
    await collection.create_index(
        [("email", 1), ("date", 1)], unique=True, name="reservation_email_per_day"
    )
    await collection.create_index(
        [("phone", 1), ("date", 1)], unique=True, name="reservation_phone_per_day"
    )
    await collection.insert_one(
        {
            "reservation_id": "RES-OLD",
            "email": "ana@example.com",
            "phone": "+34612345678",
            "date": "2030-02-28",
            "status": "cancelled",
        }
    )

    await reservation_repository.ensure_indexes()

    indexes = await collection.index_information()
    for name in ("reservation_email_per_day", "reservation_phone_per_day"):
        assert indexes[name]["partialFilterExpression"] == {"status": "confirmed"}
    await collection.insert_one(
        {
            "reservation_id": "RES-NEW",
            "email": "ana@example.com",
            "phone": "+34612345678",
            "date": "2030-02-28",
            "status": "confirmed",
        }
    )
