# app/service/reservation.py
import uuid
from typing import List
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

from app.models.reservation import ReservationCreate, ReservationUpdate, ReservationInDB
from app.repository.reservation import reservation_repository
from app.core.exceptions import ReservationNotFoundException, DatabaseException

class ReservationService:

    async def create_reservation(self, reservation_in: ReservationCreate) -> ReservationInDB:
        reservation = ReservationInDB(
            reservation_id="RES-" + str(uuid.uuid4())[:8],
            customer_name=reservation_in.customer_name,
            email=reservation_in.email,
            phone=reservation_in.phone,
            date=reservation_in.date,
            time=reservation_in.time,
            guests=reservation_in.guests,
            status="confirmed",
            created_at=datetime.now(timezone.utc)
        )
        try:
            res_dict = reservation.model_dump()
            await reservation_repository.create_reservation(res_dict)
            return reservation
        except PyMongoError as e:
            raise DatabaseException(f"Error creating reservation: {str(e)}")

    async def get_reservation(self, reservation_id: str) -> ReservationInDB:
        try:
            doc = await reservation_repository.get_reservation(reservation_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error fetching reservation: {str(e)}")

        if not doc:
            raise ReservationNotFoundException(reservation_id)

        return ReservationInDB(**doc)

    async def list_reservations(self) -> List[ReservationInDB]:
        try:
            docs = await reservation_repository.list_reservations()
            return [ReservationInDB(**doc) for doc in docs]
        except PyMongoError as e:
            raise DatabaseException(f"Error listing reservations: {str(e)}")

    async def update_reservation(self, reservation_id: str, reservation_in: ReservationUpdate) -> ReservationInDB:
        try:
            existing_doc = await reservation_repository.get_reservation(reservation_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error fetching reservation for update: {str(e)}")

        if not existing_doc:
            raise ReservationNotFoundException(reservation_id)

        update_data = reservation_in.model_dump(exclude_unset=True)
        if update_data:
            try:
                await reservation_repository.update_reservation(reservation_id, update_data)
                existing_doc.update(update_data)
            except PyMongoError as e:
                raise DatabaseException(f"Error updating reservation: {str(e)}")

        return ReservationInDB(**existing_doc)

    async def delete_reservation(self, reservation_id: str) -> None:
        try:
            success = await reservation_repository.delete_reservation(reservation_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error deleting reservation: {str(e)}")

        if not success:
            raise ReservationNotFoundException(reservation_id)

reservation_service = ReservationService()