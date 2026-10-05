# app/models/reservation.py
from datetime import date as Date, datetime, time as Time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import phonenumbers
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator, model_validator


def normalize_phone_number(value: str) -> str:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Enter a valid phone number.")

    try:
        parsed = phonenumbers.parse(value, "ES")
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Enter a valid phone number.") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Enter a valid phone number.")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def restaurant_now() -> datetime:
    return datetime.now(ZoneInfo("Europe/Madrid"))


def validate_reservation_date(reservation_date: Date, today: Date) -> None:
    if reservation_date < today or reservation_date > today + timedelta(days=13):
        raise ValueError("Reservations must be within the next 14 days.")


def validate_reservation_schedule(reservation_date: Date, reservation_time: Time) -> None:
    now = restaurant_now()
    validate_reservation_date(reservation_date, now.date())
    if reservation_date == now.date() and reservation_time < now.time().replace(tzinfo=None):
        raise ValueError("Reservations cannot be made for a time that has passed.")


def validate_service_hours(value: Optional[Time]) -> Optional[Time]:
    if value is None:
        return value
    if value.tzinfo is not None:
        raise ValueError("Reservation times must use the restaurant's local time.")
    if value < Time(12, 0) or value > Time(23, 0):
        raise ValueError("Reservations are available from 12:00 to 23:00.")
    if value.minute not in (0, 30) or value.second or value.microsecond:
        raise ValueError("Reservations are available on the half-hour.")
    return value


class ReservationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReservationContact(ReservationModel):
    email: EmailStr
    phone: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("phone", mode="before")
    @classmethod
    def canonicalize_phone(cls, value: str) -> str:
        return normalize_phone_number(value)


class ReservationData(ReservationModel):
    customer_name: str = Field(..., min_length=2, max_length=120, json_schema_extra={"example": "John Doe"})
    email: EmailStr = Field(..., json_schema_extra={"example": "john.doe@example.com"})
    phone: str = Field(..., json_schema_extra={"example": "+34612345678"})
    date: Date = Field(..., json_schema_extra={"example": "2024-06-15"})
    time: Time = Field(..., json_schema_extra={"example": "18:30"})
    guests: int = Field(..., gt=0, le=20, strict=True, json_schema_extra={"example": 4})

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("phone", mode="before")
    @classmethod
    def canonicalize_phone(cls, value: str) -> str:
        return normalize_phone_number(value)

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: Time) -> Time:
        return validate_service_hours(value)

    @field_serializer("date")
    def serialize_date(self, value: Date) -> str:
        return value.isoformat()

    @field_serializer("time")
    def serialize_time(self, value: Time) -> str:
        return value.isoformat(timespec="minutes")


class ReservationCreate(ReservationData):
    @model_validator(mode="after")
    def validate_schedule(self):
        validate_reservation_schedule(self.date, self.time)
        return self


class ReservationReplace(ReservationModel):
    date: Date
    time: Time
    guests: int = Field(..., gt=0, le=20, strict=True)

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: Time) -> Time:
        return validate_service_hours(value)

    @model_validator(mode="after")
    def validate_schedule(self):
        validate_reservation_schedule(self.date, self.time)
        return self


class ReservationUpdate(ReservationModel):
    date: Optional[Date] = None
    time: Optional[Time] = None
    guests: Optional[int] = Field(None, gt=0, le=20, strict=True)

    @field_serializer("date", when_used="json")
    def serialize_date(self, value: Optional[Date]) -> Optional[str]:
        return value.isoformat() if value is not None else None

    @field_serializer("time", when_used="json")
    def serialize_time(self, value: Optional[Time]) -> Optional[str]:
        return value.isoformat(timespec="minutes") if value is not None else None

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: Optional[Time]) -> Optional[Time]:
        return validate_service_hours(value)

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("At least one reservation field must be updated.")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Reservation fields cannot be null.")
        if self.date is not None:
            validate_reservation_date(self.date, restaurant_now().date())
        return self


class Reservation(ReservationData):
    reservation_id: str
    status: str = "confirmed"
    created_at: datetime


class ReservationInDB(Reservation):
    pass