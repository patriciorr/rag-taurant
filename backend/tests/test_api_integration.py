from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.service import menu as menu_module


pytestmark = pytest.mark.integration


@pytest.fixture
def menu_embedding(monkeypatch):
    async def get_embedding(text):
        return [0.125, 0.25, 0.5]

    monkeypatch.setattr(menu_module, "get_embedding", get_embedding)


@pytest.mark.asyncio
async def test_menu_crud_uses_real_mongo_and_stubbed_embeddings(mongo_api_client, menu_embedding):
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