import pytest
from pydantic import ValidationError

from app.models.menu import MenuItemReplace, MenuItemUpdate


def test_menu_update_accepts_a_single_changed_field():
    update = MenuItemUpdate(price=21.5)

    assert update.model_dump(exclude_unset=True) == {"price": 21.5}


def test_menu_patch_rejects_an_empty_body():
    with pytest.raises(ValidationError):
        MenuItemUpdate()


def test_menu_patch_rejects_null_values_and_unknown_fields():
    with pytest.raises(ValidationError):
        MenuItemUpdate(price=None)
    with pytest.raises(ValidationError):
        MenuItemUpdate(price=21.5, is_featured=True)


def test_menu_put_requires_every_replacement_field():
    with pytest.raises(ValidationError):
        MenuItemReplace(
            name="Gazpacho",
            description="Cold tomato soup",
            price=8.5,
            category="entrante",
        )