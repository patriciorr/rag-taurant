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
    LACTEOS = "lácteos"
    FRUTOS_SECOS = "frutos secos"
    HUEVO = "huevo"
    PESCADO = "pescado"
    MARISCO = "marisco"
    SOJA = "soja"

class MenuItemBase(BaseModel):
    name: str = Field(..., example="Paella Marinera Tradicional")
    description: str = Field(..., example="Arroz bomba cocinado a fuego lento con marisco fresco del día.")
    price: float = Field(..., gt=0, example=18.50)
    category: Category = Field(..., example=Category.PRINCIPAL)
    allergens: List[Allergen] = Field(default_factory=list, example=[Allergen.MARISCO, Allergen.PESCADO])
    is_vegan: bool = Field(default=False)
    is_vegetarian: bool = Field(default=False)
    available: bool = Field(default=True)

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[Category] = None
    allergens: Optional[List[Allergen]] = None
    is_vegan: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    available: Optional[bool] = None

class MenuItem(MenuItemBase):
    id: str

    def to_rag_text(self) -> str:
        """Formatea el plato en un texto descriptivo óptimo para la búsqueda vectorial RAG."""
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