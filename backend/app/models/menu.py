from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Category(StrEnum):
    ENTRANTE = "entrante"
    PRINCIPAL = "principal"
    POSTRE = "postre"
    BEBIDA = "bebida"


class Allergen(StrEnum):
    GLUTEN = "gluten"
    CRUSTACEOS = "crustáceos"
    HUEVO = "huevo"
    PESCADO = "pescado"
    CACAHUETE = "cacahuete"
    SOJA = "soja"
    LACTEOS = "lácteos"
    FRUTOS_SECOS = "frutos secos"
    APIO = "apio"
    MOSTAZA = "mostaza"
    SESAMO = "sésamo"
    SULFITOS = "sulfitos"
    ALTRAMUZ = "altramuces"
    MOLUSCOS = "moluscos"


class MenuModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MenuItemBase(MenuModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        json_schema_extra={"example": "Paella Marinera Tradicional"},
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        json_schema_extra={
            "example": "Arroz bomba cocinado a fuego lento con marisco fresco del día."
        },
    )
    price: float = Field(..., gt=0, json_schema_extra={"example": 18.50})
    category: Category = Field(..., json_schema_extra={"example": Category.PRINCIPAL})
    allergens: list[Allergen] = Field(
        default_factory=list, json_schema_extra={"example": [Allergen.MOLUSCOS, Allergen.PESCADO]}
    )
    is_vegan: bool = Field(default=False)
    is_vegetarian: bool = Field(default=False)
    available: bool = Field(default=True)
    image_url: str | None = Field(
        default=None,
        pattern=r"^/assets/menu/[a-z0-9-]+\.jpg$",
        json_schema_extra={"example": "/assets/menu/gazpacho.jpg"},
    )


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemReplace(MenuModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1, max_length=2000)
    price: float = Field(..., gt=0)
    category: Category
    allergens: list[Allergen]
    is_vegan: bool
    is_vegetarian: bool
    available: bool
    image_url: str | None = Field(
        default=None,
        pattern=r"^/assets/menu/[a-z0-9-]+\.jpg$",
        json_schema_extra={"example": "/assets/menu/gazpacho.jpg"},
    )


class MenuItemUpdate(MenuModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, min_length=1, max_length=2000)
    price: float | None = Field(None, gt=0)
    category: Category | None = None
    allergens: list[Allergen] | None = None
    is_vegan: bool | None = None
    is_vegetarian: bool | None = None
    available: bool | None = None
    image_url: str | None = Field(
        default=None,
        pattern=r"^/assets/menu/[a-z0-9-]+\.jpg$",
        json_schema_extra={"example": "/assets/menu/gazpacho.jpg"},
    )

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("At least one menu item field must be updated.")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Menu item fields cannot be null.")
        return self


class MenuItem(MenuItemBase):
    id: str

    def to_rag_text(self) -> str:
        """Formats the menu item into a descriptive text suitable for RAG vector search."""
        diet_labels = []
        if self.is_vegan:
            diet_labels.append("Apto para veganos")
        if self.is_vegetarian:
            diet_labels.append("Apto para vegetarianos")

        allergens_str = (
            ", ".join([a.value for a in self.allergens]) if self.allergens else "Ninguno registrado"
        )
        diets_str = ", ".join(diet_labels) if diet_labels else "Opción no vegetariana/vegana"

        return (
            f"Plato: {self.name}\n"
            f"Categoría: {self.category.value.capitalize()}\n"
            f"Precio: {self.price:.2f}€\n"
            f"Descripción: {self.description}\n"
            f"Alérgenos presentes: {allergens_str}\n"
            f"Preferencias dietéticas: {diets_str}\n"
            f"Disponible: {'Sí' if self.available else 'No'}"
        )
