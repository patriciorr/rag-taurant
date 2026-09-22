# app/api/reservation.py
from typing import List
from fastapi import APIRouter, status
from app.models.reservation import Reservation, ReservationCreate, ReservationUpdate
from app.service.reservation import reservation_service

router = APIRouter(prefix="/reservation", tags=["Reservation"])

@router.get("/", response_model=List[Reservation])
async def get_all_reservations():
    return await reservation_service.list_reservations()

@router.post("/", response_model=Reservation, status_code=status.HTTP_201_CREATED)
async def create_reservation(reservation_in: ReservationCreate):
    return await reservation_service.create_reservation(reservation_in)

@router.get("/{reservation_id}", response_model=Reservation)
async def get_reservation(reservation_id: str):
    return await reservation_service.get_reservation(reservation_id)

@router.put("/{reservation_id}", response_model=Reservation)
async def update_reservation(reservation_id: str, reservation_in: ReservationUpdate):
    return await reservation_service.update_reservation(reservation_id, reservation_in)

@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(reservation_id: str):
    await reservation_service.delete_reservation(reservation_id)