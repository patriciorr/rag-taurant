from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response

from app.service.assets import get_asset

router = APIRouter(prefix="/assets", tags=["Assets"])

MenuImageName = Annotated[str, Path(pattern=r"^[a-z0-9-]+\.jpg$")]


@router.get("/menu/{filename}")
async def menu_image(filename: MenuImageName):
    asset = await get_asset(f"menu/{filename}")
    if asset is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    body, content_type = asset
    return Response(
        content=body,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
