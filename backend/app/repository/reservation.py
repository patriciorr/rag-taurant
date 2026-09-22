# app/repository/reservation.py
from typing import List, Optional
from app.core.database import db_instance

class ReservationRepository:
    @property
    def collection(self):
        return db_instance.db['reservations']

    async def create_reservation(self, reservation_data: dict) -> dict:
        await self.collection.insert_one(reservation_data)
        reservation_data.pop("_id", None)
        return reservation_data

    async def get_reservation(self, reservation_id: str) -> Optional[dict]:
        return await self.collection.find_one({"reservation_id": reservation_id}, {"_id": 0})

    async def list_reservations(self) -> List[dict]:
        cursor = self.collection.find({}, {"_id": 0})
        return [doc async for doc in cursor]

    async def update_reservation(self, reservation_id: str, update_data: dict) -> bool:
        result = await self.collection.update_one(
            {"reservation_id": reservation_id},
            {"$set": update_data}
        )
        return result.matched_count > 0

    async def delete_reservation(self, reservation_id: str) -> bool:
        result = await self.collection.delete_one({"reservation_id": reservation_id})
        return result.deleted_count > 0

reservation_repository = ReservationRepository()