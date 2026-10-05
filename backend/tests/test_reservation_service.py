from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ReservationConflictException, ReservationNotFoundException
from app.models import reservation as reservation_models
from app.models.reservation import ReservationContact, ReservationCreate, ReservationUpdate
from app.service import reservation as reservation_module
from app.service.reservation import ReservationService


@pytest.fixture(autouse=True)
def reservation_clock(monkeypatch):
    now = datetime(2030, 2, 27, 10, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)


def reservation_document():
    return {
        "reservation_id": "RES-1",
        "customer_name": "Ana Perez",
        "email": "ana@example.com",
        "phone": "+34612345678",
        "date": "2030-02-28",
        "time": "18:30",
        "guests": 2,
        "status": "confirmed",
        "created_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
    }


@pytest.mark.asyncio
async def test_get_reservation_requires_both_matching_contact_values(monkeypatch):
    service = ReservationService()

    async def get_reservation(reservation_id):
        return reservation_document()

    monkeypatch.setattr(reservation_module.reservation_repository, "get_reservation", get_reservation)

    reservation = await service.get_reservation(
        "RES-1",
        ReservationContact(email="ANA@example.com", phone="612 345 678"),
    )

    assert reservation.reservation_id == "RES-1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "contact",
    [
        ReservationContact(email="other@example.com", phone="+34612345678"),
        ReservationContact(email="ana@example.com", phone="+34600000000"),
    ],
)
async def test_get_reservation_hides_missing_or_mismatched_contacts(monkeypatch, contact):
    service = ReservationService()

    async def get_reservation(reservation_id):
        return reservation_document()

    monkeypatch.setattr(reservation_module.reservation_repository, "get_reservation", get_reservation)

    with pytest.raises(ReservationNotFoundException):
        await service.get_reservation("RES-1", contact)


@pytest.mark.asyncio
async def test_create_reservation_serializes_date_and_time_for_mongo(monkeypatch):
    service = ReservationService()
    persisted = {}

    async def create_reservation(reservation_data):
        persisted.update(reservation_data)

    monkeypatch.setattr(reservation_module.reservation_repository, "create_reservation", create_reservation)
    request = ReservationCreate(
        customer_name="Ana Perez",
        email="ana@example.com",
        phone="612 345 678",
        date="2030-02-28",
        time="18:30",
        guests=2,
    )

    await service.create_reservation(request)

    assert persisted["date"] == "2030-02-28"
    assert persisted["time"] == "18:30"
    assert persisted["phone"] == "+34612345678"


@pytest.mark.asyncio
async def test_patch_reservation_changes_only_editable_fields(monkeypatch):
    service = ReservationService()
    updates = {}

    async def get_reservation(reservation_id):
        return reservation_document()

    async def update_reservation(reservation_id, update_data):
        updates.update(update_data)
        return True

    monkeypatch.setattr(reservation_module.reservation_repository, "get_reservation", get_reservation)
    monkeypatch.setattr(reservation_module.reservation_repository, "update_reservation", update_reservation)

    updated = await service.update_reservation(
        "RES-1",
        ReservationUpdate(guests=4),
        ReservationContact(email="ana@example.com", phone="+34612345678"),
    )

    assert updates == {"guests": 4}
    assert updated.guests == 4
    assert updated.email == "ana@example.com"


@pytest.mark.asyncio
async def test_duplicate_contact_for_the_same_day_becomes_a_conflict(monkeypatch):
    service = ReservationService()

    async def create_reservation(reservation_data):
        raise DuplicateKeyError("duplicate reservation contact")

    monkeypatch.setattr(reservation_module.reservation_repository, "create_reservation", create_reservation)
    request = ReservationCreate(
        customer_name="Ana Perez",
        email="ana@example.com",
        phone="612 345 678",
        date="2030-02-28",
        time="18:30",
        guests=2,
    )

    with pytest.raises(ReservationConflictException):
        await service.create_reservation(request)


@pytest.mark.asyncio
async def test_cancellation_is_safe_to_retry_and_keeps_the_reservation(monkeypatch):
    service = ReservationService()
    stored = reservation_document()
    contact = ReservationContact(email="ana@example.com", phone="+34612345678")

    async def get_reservation(reservation_id):
        return stored

    async def cancel_reservation(reservation_id):
        stored["status"] = "cancelled"
        return True

    monkeypatch.setattr(reservation_module.reservation_repository, "get_reservation", get_reservation)
    monkeypatch.setattr(reservation_module.reservation_repository, "cancel_reservation", cancel_reservation)

    await service.cancel_reservation("RES-1", contact)
    await service.cancel_reservation("RES-1", contact)

    retained = await service.get_reservation("RES-1", contact)
    assert retained.status == "cancelled"