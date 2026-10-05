import pytest

from app.models.menu import MenuItemReplace
from app.service import menu as menu_module
from app.service.menu import MenuService


@pytest.mark.asyncio
async def test_replace_menu_item_rebuilds_embedding_and_returns_complete_item(monkeypatch):
    service = MenuService()
    persisted = {}

    async def get_menu_item(dish_id):
        return {
            "id": dish_id,
            "name": "Gazpacho",
            "description": "Cold tomato soup",
            "price": 8.5,
            "category": "entrante",
            "allergens": [],
            "is_vegan": True,
            "is_vegetarian": True,
            "available": True,
            "embedding": [0.1],
        }

    async def update_menu_item(dish_id, updated_item):
        persisted.update(updated_item)
        return True

    async def get_embedding(text):
        return [0.2, 0.3]

    monkeypatch.setattr(menu_module.menu_repository, "get_menu_item", get_menu_item)
    monkeypatch.setattr(menu_module.menu_repository, "update_menu_item", update_menu_item)
    monkeypatch.setattr(menu_module, "get_embedding", get_embedding)

    updated = await service.replace_menu_item(
        "dish-1",
        MenuItemReplace(
            name="Paella",
            description="Rice with vegetables",
            price=19.5,
            category="principal",
            allergens=[],
            is_vegan=True,
            is_vegetarian=True,
            available=True,
        ),
    )

    assert updated.name == "Paella"
    assert persisted["name"] == "Paella"
    assert persisted["embedding"] == [0.2, 0.3]