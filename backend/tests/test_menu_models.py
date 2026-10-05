import pytest
from pydantic import ValidationError

from app.models.menu import Allergen, MenuItemReplace, MenuItemUpdate


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


def test_menu_images_are_validated_local_asset_references():
    assert MenuItemUpdate(image_url="/assets/menu/gazpacho.jpg").image_url == (
        "/assets/menu/gazpacho.jpg"
    )
    with pytest.raises(ValidationError):
        MenuItemUpdate(image_url="http://localstack:4566/bucket/gazpacho.jpg")
    with pytest.raises(ValidationError):
        MenuItemUpdate(image_url="/assets/menu/../private.jpg")


def test_allergen_model_covers_the_complete_eu_allergen_list():
    assert {allergen.value for allergen in Allergen} == {
        "gluten",
        "crustáceos",
        "huevo",
        "pescado",
        "cacahuete",
        "soja",
        "lácteos",
        "frutos secos",
        "apio",
        "mostaza",
        "sésamo",
        "sulfitos",
        "altramuces",
        "moluscos",
    }