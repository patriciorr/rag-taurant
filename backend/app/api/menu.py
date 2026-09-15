# app/api/menu.py
import json
import uuid
import os
from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.menu import MenuItem, MenuItemCreate, MenuItemUpdate
from app.rag.vectorstore import vector_store
from app.core.config import settings

router = APIRouter(prefix="/menu", tags=["Menú"])

def _load_dishes_from_file() -> List[MenuItem]:
    if not os.path.exists(settings.MENU_DATA_PATH):
        return []
    with open(settings.MENU_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [MenuItem(**item) for item in data]

def _save_dishes_to_file(dishes: List[MenuItem]):
    with open(settings.MENU_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump([d.model_dump() for d in dishes], f, ensure_ascii=False, indent=2)

@router.get("/search")
def search_dishes_vectorial(query: str, limit: int = 3):
    """
    Endpoint de prueba para realizar búsquedas semánticas directas en ChromaDB.
    
    Parámetros:
    - query: Texto de búsqueda en lenguaje natural (ej. 'algo con marisco', 'postre casero')
    - limit: Número máximo de resultados similares a devolver (por defecto: 3)
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="El parámetro 'query' no puede estar vacío.")
    
    results = vector_store.search_similar_dishes(query=query, n_results=limit)
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }

@router.get("/", response_model=List[MenuItem])
def get_all_dishes():
    """Obtiene la lista completa de platos."""
    return _load_dishes_from_file()

@router.post("/", response_model=MenuItem, status_code=status.HTTP_201_CREATED)
def create_dish(dish_in: MenuItemCreate):
    """Crea un nuevo plato en la BD local y lo indexa automáticamente en ChromaDB."""
    dishes = _load_dishes_from_file()
    
    new_dish = MenuItem(
        id=str(uuid.uuid4())[:8],
        **dish_in.model_dump()
    )
    dishes.append(new_dish)
    _save_dishes_to_file(dishes)
    
    # Sincronización con ChromaDB
    vector_store.upsert_dish(new_dish)
    
    return new_dish

@router.put("/{dish_id}", response_model=MenuItem)
def update_dish(dish_id: str, dish_in: MenuItemUpdate):
    """Actualiza un plato y regenera su vector en ChromaDB."""
    dishes = _load_dishes_from_file()
    idx = next((i for i, d in enumerate(dishes) if d.id == dish_id), None)
    
    if idx is None:
        raise HTTPException(status_code=404, detail="Plato no encontrado")
    
    updated_data = dishes[idx].model_dump()
    update_dict = dish_in.model_dump(exclude_unset=True)
    updated_data.update(update_dict)
    
    updated_dish = MenuItem(**updated_data)
    dishes[idx] = updated_dish
    _save_dishes_to_file(dishes)
    
    # Sincronización vectorial
    vector_store.upsert_dish(updated_dish)
    
    return updated_dish

@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dish(dish_id: str):
    """Elimina un plato y borra su registro vectorial en ChromaDB."""
    dishes = _load_dishes_from_file()
    filtered = [d for d in dishes if d.id != dish_id]
    
    if len(filtered) == len(dishes):
        raise HTTPException(status_code=404, detail="Plato no encontrado")
    
    _save_dishes_to_file(filtered)
    vector_store.delete_dish(dish_id)