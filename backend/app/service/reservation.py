# app/service/reservation.py
import uuid
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.reservation import ReservationContact, ReservationCreate, ReservationReplace, ReservationUpdate, ReservationInDB, validate_reservation_schedule
from app.repository.reservation import reservation_repository
from app.core.exceptions import DatabaseException, ReservationConflictException, ReservationNotFoundException, ReservationValidationException

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
            res_dict["date"] = reservation.date.isoformat()
            res_dict["time"] = reservation.time.isoformat(timespec="minutes")
            await reservation_repository.create_reservation(res_dict)
            return reservation
        except DuplicateKeyError as e:
            raise ReservationConflictException() from e
        except PyMongoError as e:
            raise DatabaseException(f"Error creating reservation: {str(e)}")

    async def get_reservation(self, reservation_id: str, contact: ReservationContact) -> ReservationInDB:
        _, reservation = await self._get_authorized_reservation(reservation_id, contact)
        return reservation

    async def _get_authorized_reservation(
        self,
        reservation_id: str,
        contact: ReservationContact,
    ) -> tuple[dict, ReservationInDB]:
        try:
            doc = await reservation_repository.get_reservation(reservation_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error fetching reservation: {str(e)}")

        if not doc:
            raise ReservationNotFoundException(reservation_id)

        reservation = ReservationInDB(**doc)
        if reservation.email != contact.email or reservation.phone != contact.phone:
            raise ReservationNotFoundException(reservation_id)

        return doc, reservation

    async def replace_reservation(
        self,
        reservation_id: str,
        reservation_in: ReservationReplace,
        contact: ReservationContact,
    ) -> ReservationInDB:
        return await self._update_reservation(reservation_id, reservation_in.model_dump(), contact)

    async def update_reservation(
        self,
        reservation_id: str,
        reservation_in: ReservationUpdate,
        contact: ReservationContact,
    ) -> ReservationInDB:
        return await self._update_reservation(
            reservation_id,
            reservation_in.model_dump(exclude_unset=True),
            contact,
        )

    async def _update_reservation(
        self,
        reservation_id: str,
        update_data: dict,
        contact: ReservationContact,
    ) -> ReservationInDB:
        existing_doc, existing = await self._get_authorized_reservation(reservation_id, contact)
        if existing_doc.get("status") == "cancelled":
            raise ReservationValidationException("Cancelled reservations cannot be modified.")
        reservation_date = update_data.get("date", existing.date)
        reservation_time = update_data.get("time", existing.time)
        try:
            validate_reservation_schedule(reservation_date, reservation_time)
        except ValueError as exc:
            raise ReservationValidationException(str(exc)) from exc

        if "date" in update_data:
            update_data["date"] = update_data["date"].isoformat()
        if "time" in update_data:
            update_data["time"] = update_data["time"].isoformat(timespec="minutes")

        try:
            updated = await reservation_repository.update_reservation(reservation_id, update_data)
        except DuplicateKeyError as e:
            raise ReservationConflictException() from e
        except PyMongoError as e:
            raise DatabaseException(f"Error updating reservation: {str(e)}")

        if not updated:
            raise ReservationNotFoundException(reservation_id)
        existing_doc.update(update_data)
        return ReservationInDB(**existing_doc)

    async def cancel_reservation(self, reservation_id: str, contact: ReservationContact) -> None:
        await self._get_authorized_reservation(reservation_id, contact)
        try:
            success = await reservation_repository.cancel_reservation(reservation_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error canceling reservation: {str(e)}")

        if not success:
            raise ReservationNotFoundException(reservation_id)

reservation_service = ReservationService()