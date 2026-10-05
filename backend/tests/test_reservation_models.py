from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.models import reservation as reservation_models
from app.models.reservation import ReservationCreate, ReservationInDB, ReservationUpdate


def make_reservation_data(**overrides):
    data = {
        "customer_name": "Ana Perez",
        "email": "ana@example.com",
        "phone": "+34612345678",
        "date": "2030-02-28",
        "time": "18:30",
        "guests": 2,
    }
    return {**data, **overrides}


@pytest.fixture(autouse=True)
def reservation_clock(monkeypatch):
    now = datetime(2030, 2, 27, 10, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)


def test_reservation_date_is_parsed_as_a_calendar_date():
    reservation = ReservationCreate(**make_reservation_data())

    assert reservation.date == date(2030, 2, 28)
    assert reservation.time == time(18, 30)


def test_reservation_rejects_an_impossible_calendar_date():
    with pytest.raises(ValidationError):
        ReservationCreate(**make_reservation_data(date="2030-02-30"))


def test_reservation_rejects_a_past_date():
    yesterday = datetime.now(ZoneInfo("Europe/Madrid")).date() - timedelta(days=1)

    with pytest.raises(ValidationError):
        ReservationCreate(**make_reservation_data(date=yesterday.isoformat()))


def test_reservation_accepts_the_last_date_in_the_booking_horizon(monkeypatch):
    now = datetime(2030, 2, 28, 10, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)

    reservation = ReservationCreate(**make_reservation_data(date="2030-03-13"))

    assert reservation.date == date(2030, 3, 13)


def test_reservation_rejects_dates_beyond_the_booking_horizon(monkeypatch):
    now = datetime(2030, 2, 28, 10, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)

    with pytest.raises(ValidationError):
        ReservationCreate(**make_reservation_data(date="2030-03-14"))


def test_reservation_allows_the_start_of_service_hours():
    reservation = ReservationCreate(**make_reservation_data(time="12:00"))

    assert reservation.time == time(12, 0)


@pytest.mark.parametrize("reservation_time", ["12:00", "12:30", "22:30", "23:00"])
def test_reservation_accepts_half_hour_service_slots(reservation_time):
    reservation = ReservationCreate(**make_reservation_data(time=reservation_time))

    assert reservation.time == time.fromisoformat(reservation_time)


@pytest.mark.parametrize("reservation_time", ["12:15", "22:45"])
def test_reservation_rejects_times_between_service_slots(reservation_time):
    with pytest.raises(ValidationError):
        ReservationCreate(**make_reservation_data(time=reservation_time))


def test_reservation_rejects_times_outside_service_hours():
    with pytest.raises(ValidationError):
        ReservationCreate(**make_reservation_data(time="11:59"))


def test_reservation_rejects_a_time_that_has_passed_today(monkeypatch):
    now = datetime(2030, 2, 28, 18, 30, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)

    with pytest.raises(ValidationError):
        ReservationCreate(**make_reservation_data(date="2030-02-28", time="18:29"))


def test_reservation_model_dump_keeps_mongo_compatible_schedule_strings():
    reservation = ReservationInDB(
        reservation_id="RES-1",
        customer_name="Ana Perez",
        email="ana@example.com",
        phone="612 345 678",
        date="2030-02-28",
        time="18:30",
        guests=2,
        created_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    values = reservation.model_dump()

    assert values["date"] == "2030-02-28"
    assert values["time"] == "18:30"


def test_reservation_phone_is_normalized_to_spanish_e164():
    reservation = ReservationCreate(**make_reservation_data(phone="612 345 678"))

    assert reservation.phone == "+34612345678"


def test_reservation_update_can_change_only_guest_count():
    update = ReservationUpdate(guests=4)

    assert update.model_dump(exclude_unset=True) == {"guests": 4}


def test_reservation_update_does_not_allow_changing_contact_details():
    with pytest.raises(ValidationError):
        ReservationUpdate(email="other@example.com")