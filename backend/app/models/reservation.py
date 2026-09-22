# app/models/reservation.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class Reservation(BaseModel):
    reservation_id: str = Field(..., description="Unique identifier for the reservation", example="RES-69c1e156")
    customer_name: str = Field(..., description="Full name of the customer", example="John Doe")
    email: EmailStr = Field(..., description="Contact email address", example="john.doe@example.com")
    phone: str = Field(..., description="Contact phone number", example="+1234567890")
    date: str = Field(..., description="Reservation date in YYYY-MM-DD format", example="2024-06-15")
    time: str = Field(..., description="Reservation time in HH:MM format", example="18:30")
    guests: int = Field(..., description="Number of guests for the reservation", example=4)
    status: str = Field(default="confirmed", description="Reservation status", example="confirmed")
    created_at: datetime = Field(..., description="Timestamp when the reservation was created", example="2024-06-01T12:00:00Z")

class ReservationCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, description="Full name of the customer", example="John Doe")
    email: EmailStr = Field(..., description="Contact email address", example="john.doe@example.com")
    phone: str = Field(..., pattern=r"^\+?[0-9]{9,15}$", description="Contact phone number", example="+1234567890")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", gt="1900-01-01", le="2100-12-31", description="Reservation date in YYYY-MM-DD format. Allowed range: 1900-01-01 - 2100-12-31.", example="2024-06-15")
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$", gt="12:00", le="23:00", description="Reservation time in HH:MM format. Allowed range: 12:00 - 23:00.", example="18:30")
    guests: int = Field(..., gt=0, le=20, description="Number of guests (maximum 20)", example=4)

class ReservationUpdate(BaseModel):
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", gt="1900-01-01", le="2100-12-31", description="Reservation date in YYYY-MM-DD format. Allowed range: 1900-01-01 - 2100-12-31.", example="2024-06-15")
    time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", gt="12:00", le="23:00", description="Reservation time in HH:MM format. Allowed range: 12:00 - 23:00.", example="23:00")
    guests: Optional[int] = Field(None, gt=0, le=20, description="Number of guests (maximum 20)", example=2)
    customer_name: Optional[str] = Field(None, min_length=2, description="Full name of the customer", example="Jane Doe")

class ReservationInDB(ReservationCreate):
    reservation_id: str = Field(..., description="Unique identifier for the reservation", example="RES-69c1e156")
    created_at: datetime = Field(..., description="Timestamp when the reservation was created", example="2024-06-01T12:00:00Z")
    status: str = Field(default="confirmed", description="Reservation status", example="confirmed")