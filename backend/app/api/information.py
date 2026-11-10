from fastapi import APIRouter

from app.core.restaurant_info import RESTAURANT_INFORMATION

router = APIRouter(prefix="/information", tags=["Restaurant information"])


@router.get("/")
def get_restaurant_information():
    return RESTAURANT_INFORMATION
