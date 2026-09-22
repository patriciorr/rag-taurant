# app/models/menu.py
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class Category(str, Enum):
    ENTRANTE = "entrante"
    PRINCIPAL = "principal"
    POSTRE = "postre"
    BEBIDA = "bebida"

class Allergen(str, Enum):
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

class MenuItemBase(BaseModel):
    name: str = Field(..., example="Paella Marinera Tradicional")
    description: str = Field(..., example="Arroz bomba cocinado a fuego lento con marisco fresco del día.")
    price: float = Field(..., gt=0, example=18.50)
    category: Category = Field(..., example=Category.PRINCIPAL)
    allergens: List[Allergen] = Field(default_factory=list, example=[Allergen.MOLUSCOS, Allergen.PESCADO])
    is_vegan: bool = Field(default=False)
    is_vegetarian: bool = Field(default=False)
    available: bool = Field(default=True)

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(..., example="Paella de Carne")
    description: Optional[str] = Field(..., example="Arroz bomba cocinado a fuego lento con pollo y verduras.")
    price: Optional[float] = Field(None, gt=0, example=18.50)
    category: Optional[Category] = Field(None, example=Category.PRINCIPAL)
    allergens: Optional[List[Allergen]] = Field(None, example=[Allergen.SOJA, Allergen.SESAMO])
    is_vegan: Optional[bool] = Field(..., example=False)
    is_vegetarian: Optional[bool] = Field(..., example=False)
    available: Optional[bool] = Field(..., example=True)

class MenuItem(MenuItemBase):
    id: str

    def to_rag_text(self) -> str:
        """Formats the menu item into a descriptive text suitable for RAG vector search."""
        diet_labels = []
        if self.is_vegan:
            diet_labels.append("Apto para veganos")
        if self.is_vegetarian:
            diet_labels.append("Apto para vegetarianos")
        
        allergens_str = ", ".join([a.value for a in self.allergens]) if self.allergens else "Sin alérgenos comunes"
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