# app/api/menu.py
from typing import List
from fastapi import APIRouter, HTTPException, Query, status
from app.models.menu import MenuItem, MenuItemCreate, MenuItemReplace, MenuItemUpdate
from app.service.menu import menu_service

router = APIRouter(prefix="/menu", tags=["Menu"])

@router.get("/search")
async def search_dishes_vectorial(
    query: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(3, ge=1, le=20),
):
    query = query.strip()
    if not query:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Query cannot be empty.")

    results = await menu_service.search_similar_dishes(query=query, limit=limit)
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }

@router.get("/", response_model=List[MenuItem])
async def get_all_dishes():
    return await menu_service.list_menu()

@router.get("/{dish_id}", response_model=MenuItem)
async def get_dish(dish_id: str):
    return await menu_service.get_menu_item(dish_id)

@router.post("/", response_model=MenuItem, status_code=status.HTTP_201_CREATED)
async def create_dish(dish_in: MenuItemCreate):
    return await menu_service.create_menu_item(dish_in)

@router.put("/{dish_id}", response_model=MenuItem)
async def replace_dish(dish_id: str, dish_in: MenuItemReplace):
    return await menu_service.replace_menu_item(dish_id, dish_in)

@router.patch("/{dish_id}", response_model=MenuItem)
async def update_dish(dish_id: str, dish_in: MenuItemUpdate):
    return await menu_service.update_menu_item(dish_id, dish_in)

@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dish(dish_id: str):
    await menu_service.delete_menu_item(dish_id)