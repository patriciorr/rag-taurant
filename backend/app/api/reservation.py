# app/api/reservation.py
from fastapi import APIRouter, Depends, Header, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from app.models.reservation import Reservation, ReservationContact, ReservationCreate, ReservationReplace, ReservationUpdate
from app.service.reservation import reservation_service

router = APIRouter(prefix="/reservations", tags=["Reservation"])

def get_reservation_contact(
    email: str = Header(..., alias="X-Reservation-Email"),
    phone: str = Header(..., alias="X-Reservation-Phone"),
) -> ReservationContact:
    try:
        return ReservationContact(email=email, phone=phone)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

@router.post("/", response_model=Reservation, status_code=status.HTTP_201_CREATED)
async def create_reservation(reservation_in: ReservationCreate):
    return await reservation_service.create_reservation(reservation_in)

@router.get("/{reservation_id}", response_model=Reservation)
async def get_reservation(
    reservation_id: str,
    contact: ReservationContact = Depends(get_reservation_contact),
):
    return await reservation_service.get_reservation(reservation_id, contact)

@router.put("/{reservation_id}", response_model=Reservation)
async def replace_reservation(
    reservation_id: str,
    reservation_in: ReservationReplace,
    contact: ReservationContact = Depends(get_reservation_contact),
):
    return await reservation_service.replace_reservation(reservation_id, reservation_in, contact)

@router.patch("/{reservation_id}", response_model=Reservation)
async def update_reservation(
    reservation_id: str,
    reservation_in: ReservationUpdate,
    contact: ReservationContact = Depends(get_reservation_contact),
):
    return await reservation_service.update_reservation(reservation_id, reservation_in, contact)

@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reservation(
    reservation_id: str,
    contact: ReservationContact = Depends(get_reservation_contact),
):
    await reservation_service.cancel_reservation(reservation_id, contact)