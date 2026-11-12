from app.core.database import db_instance
from app.rag.vector_search import vector_search


class MenuRepository:
    @property
    def collection(self):
        return db_instance.db["menu"]

    async def list_menu(self) -> list[dict]:
        cursor = self.collection.find(
            {}, {"_id": 0, "embedding": 0, "embedding_model": 0, "embedding_dimensions": 0}
        )
        return [doc async for doc in cursor]

    async def get_menu_item(self, dish_id: str) -> dict | None:
        return await self.collection.find_one(
            {"id": dish_id},
            {"_id": 0, "embedding": 0, "embedding_model": 0, "embedding_dimensions": 0},
        )

    async def add_menu_item(self, item: dict) -> None:
        await self.collection.insert_one(item)

    async def update_menu_item(self, dish_id: str, updated_item: dict) -> bool:
        result = await self.collection.update_one({"id": dish_id}, {"$set": updated_item})
        return result.matched_count > 0

    async def delete_menu_item(self, dish_id: str) -> bool:
        result = await self.collection.delete_one({"id": dish_id})
        return result.deleted_count > 0

    async def vector_search(self, query_vector: list[float], limit: int = 3) -> list[dict]:
        return await vector_search("menu", query_vector, limit)


menu_repository = MenuRepository()
