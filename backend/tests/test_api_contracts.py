from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.api import menu as menu_api
from app.models import reservation as reservation_models
from app.service import reservation as reservation_service
from main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def menu_item_response():
    return {
        "id": "dish-1",
        "name": "Gazpacho",
        "description": "Cold tomato soup",
        "price": 8.5,
        "category": "entrante",
        "allergens": [],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
    }


def test_menu_validation_errors_have_the_shared_error_code(client):
    response = client.post("/api/v1/menu/", json={})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_chat_endpoint_awaits_the_chatbot_runner(client, monkeypatch):
    async def invoke(input_data, config):
        assert input_data == {"input": "Hola"}
        assert config == {"configurable": {"session_id": "tab-1"}}
        return {"output": "¡Hola!"}

    monkeypatch.setattr(chat_api.rag_chatbot, "ainvoke", invoke)

    response = client.post(
        "/api/v1/chat/",
        json={"message": "Hola", "session_id": "tab-1"},
    )

    assert response.status_code == 200
    assert response.json() == {"response": "¡Hola!", "session_id": "tab-1"}


def test_menu_search_rejects_whitespace_only_queries(client, monkeypatch):
    async def search_similar_dishes(query, limit):
        pytest.fail("Whitespace-only queries must not reach the embedding service.")

    monkeypatch.setattr(menu_api.menu_service, "search_similar_dishes", search_similar_dishes)
    response = client.get("/api/v1/menu/search", params={"query": "   "})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_menu_patch_accepts_a_single_changed_field(client, monkeypatch):
    async def update_menu_item(dish_id, dish_in):
        return menu_item_response()

    monkeypatch.setattr(menu_api.menu_service, "update_menu_item", update_menu_item)

    response = client.patch("/api/v1/menu/dish-1", json={"price": 9.5})

    assert response.status_code == 200
    assert response.json()["id"] == "dish-1"


def test_menu_put_requires_a_complete_replacement(client):
    response = client.put("/api/v1/menu/dish-1", json={"price": 9.5})

    assert response.status_code == 422


def test_reservation_detail_requires_contact_headers(client):
    response = client.get("/api/v1/reservations/RES-1")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_reservation_collection_is_not_publicly_listable(client):
    response = client.get("/api/v1/reservations/")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_reservation_put_requires_a_complete_replacement(client):
    response = client.put(
        "/api/v1/reservations/RES-1",
        headers={
            "X-Reservation-Email": "ana@example.com",
            "X-Reservation-Phone": "+34612345678",
        },
        json={"guests": 4},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_invalid_reservation_contact_headers_return_validation_error(client):
    response = client.get(
        "/api/v1/reservations/RES-1",
        headers={
            "X-Reservation-Email": "not-an-email",
            "X-Reservation-Phone": "not-a-phone",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("reservation_date", "reservation_time"),
    [("2030-03-14", "18:30"), ("2030-02-28", "12:15"), ("2030-02-28", "18:29")],
)
def test_reservation_create_rejects_out_of_policy_schedule(
    client,
    monkeypatch,
    reservation_date,
    reservation_time,
):
    now = datetime(2030, 2, 28, 18, 30, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)

    response = client.post(
        "/api/v1/reservations/",
        json={
            "customer_name": "Ana Perez",
            "email": "ana@example.com",
            "phone": "+34612345678",
            "date": reservation_date,
            "time": reservation_time,
            "guests": 2,
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_reservation_update_rejects_dates_beyond_the_booking_horizon(client, monkeypatch):
    now = datetime(2030, 2, 28, 10, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)

    response = client.patch(
        "/api/v1/reservations/RES-1",
        headers={
            "X-Reservation-Email": "ana@example.com",
            "X-Reservation-Phone": "+34612345678",
        },
        json={"date": "2030-03-14"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_reservation_delete_contract_cancels_using_the_contact_headers(client, monkeypatch):
    async def cancel_reservation(reservation_id, contact):
        assert reservation_id == "RES-1"
        assert contact.email == "ana@example.com"
        assert contact.phone == "+34612345678"

    monkeypatch.setattr(reservation_service.reservation_service, "cancel_reservation", cancel_reservation)

    response = client.delete(
        "/api/v1/reservations/RES-1",
        headers={
            "X-Reservation-Email": "ana@example.com",
            "X-Reservation-Phone": "+34612345678",
        },
    )

    assert response.status_code == 204


def test_internal_api_errors_do_not_leak_exception_details(client, monkeypatch):
    async def fail_to_list_menu():
        raise RuntimeError("private database credential")

    monkeypatch.setattr(menu_api.menu_service, "list_menu", fail_to_list_menu)

    response = client.get("/api/v1/menu/")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error.",
        "code": "INTERNAL_SERVER_ERROR",
    }