# app/service/menu.py
import uuid
from typing import List, Dict, Any
from pymongo.errors import PyMongoError
from app.models.menu import MenuItem, MenuItemCreate, MenuItemReplace, MenuItemUpdate
from app.repository.menu import menu_repository
from app.rag.embeddings import get_embedding
from app.core.exceptions import MenuItemNotFoundException, EmbeddingServiceException, DatabaseException

class MenuService:
    def _get_text_for_embedding(self, item: Dict[str, Any]) -> str:
        """Creates a comprehensive textual description of a menu item for embedding purposes."""
        parts = []

        if item.get("name"):
            parts.append(f"Plato: {item['name']}")
        if item.get("category"):
            parts.append(f"Categoría: {item['category']}")
        if item.get("price") is not None:
            parts.append(f"Precio: {item['price']} EUR")
        if item.get("description"):
            parts.append(f"Descripción: {item['description']}")

        is_vegan = item.get("is_vegan", False)
        is_vegetarian = item.get("is_vegetarian", False)
        parts.append(f"Apto para veganos: {'Sí' if is_vegan else 'No'}")
        parts.append(f"Apto para vegetarianos: {'Sí' if is_vegetarian else 'No'}")

        allergens = item.get("allergens", [])
        if allergens:
            allergens_str = ", ".join(allergens) if isinstance(allergens, list) else str(allergens)
            parts.append(f"Contiene alérgenos: {allergens_str}")
        else:
            parts.append("Alérgenos: Ninguno")

        return ". ".join(parts) + "."

    async def list_menu(self) -> List[MenuItem]:
        try:
            items = await menu_repository.list_menu()
            return [MenuItem(**item) for item in items]
        except PyMongoError as e:
            raise DatabaseException(f"Error listing menu: {str(e)}")

    async def get_menu_item(self, dish_id: str) -> MenuItem:
        try:
            item = await menu_repository.get_menu_item(dish_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error fetching menu item: {str(e)}")

        if not item:
            raise MenuItemNotFoundException(dish_id)

        return MenuItem(**item)

    async def create_menu_item(self, dish_in: MenuItemCreate) -> MenuItem:
        dish_id = str(uuid.uuid4())[:8]
        dish_data = dish_in.model_dump()

        text_for_rag = self._get_text_for_embedding(dish_data)

        try:
            embedding = await get_embedding(text_for_rag)
        except Exception as e:
            raise EmbeddingServiceException(f"Failed to generate embedding: {str(e)}")

        db_doc = {
            "id": dish_id,
            **dish_data,
            "embedding": embedding
        }

        try:
            await menu_repository.add_menu_item(db_doc)
        except PyMongoError as e:
            raise DatabaseException(f"Error saving menu item: {str(e)}")

        return MenuItem(id=dish_id, **dish_data)

    async def update_menu_item(self, dish_id: str, dish_in: MenuItemUpdate) -> MenuItem:
        update_data = dish_in.model_dump(exclude_unset=True, mode="json")
        return await self._update_menu_item(dish_id, update_data)

    async def replace_menu_item(self, dish_id: str, dish_in: MenuItemReplace) -> MenuItem:
        replacement_data = dish_in.model_dump(mode="json")
        return await self._update_menu_item(dish_id, replacement_data)

    async def _update_menu_item(self, dish_id: str, update_data: dict) -> MenuItem:
        try:
            existing_doc = await menu_repository.get_menu_item(dish_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error checking existing menu item: {str(e)}")

        if not existing_doc:
            raise MenuItemNotFoundException(dish_id)

        if not update_data:
            return MenuItem(**existing_doc)

        merged_data = {**existing_doc, **update_data}

        text_for_rag = self._get_text_for_embedding(merged_data)
        try:
            merged_data["embedding"] = await get_embedding(text_for_rag)
        except Exception as e:
            raise EmbeddingServiceException(f"Error updating embedding: {str(e)}")

        try:
            success = await menu_repository.update_menu_item(dish_id, merged_data)
        except PyMongoError as e:
            raise DatabaseException(f"Database error: {str(e)}")

        if not success:
            raise MenuItemNotFoundException(dish_id)

        merged_data.pop("embedding", None)
        return MenuItem(**merged_data)

    async def delete_menu_item(self, dish_id: str) -> None:
        try:
            success = await menu_repository.delete_menu_item(dish_id)
        except PyMongoError as e:
            raise DatabaseException(f"Error deleting menu item: {str(e)}")

        if not success:
            raise MenuItemNotFoundException(dish_id)

    async def search_similar_dishes(self, query: str, limit: int = 3) -> List[dict]:
        try:
            query_vector = await get_embedding(query)
        except Exception as e:
            raise EmbeddingServiceException(f"Error processing RAG query: {str(e)}")

        try:
            return await menu_repository.vector_search(query_vector, limit)
        except PyMongoError as e:
            raise DatabaseException(f"Error executing vector search: {str(e)}")

menu_service = MenuService()