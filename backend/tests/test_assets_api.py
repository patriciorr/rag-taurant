import pytest
from httpx import ASGITransport, AsyncClient

from app.api import assets
from main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_menu_image_is_served_from_bucket(client, monkeypatch):
    async def fake(key):
        assert key == "menu/gazpacho.jpg"
        return b"jpg-bytes", "image/jpeg"

    monkeypatch.setattr(assets, "get_asset", fake)
    response = await client.get("/assets/menu/gazpacho.jpg")
    assert response.status_code == 200
    assert response.content == b"jpg-bytes"
    assert "max-age" in response.headers["cache-control"]


async def test_missing_image_returns_404(client, monkeypatch):
    async def fake(key):
        return None

    monkeypatch.setattr(assets, "get_asset", fake)
    assert (await client.get("/assets/menu/nope.jpg")).status_code == 404


@pytest.mark.parametrize("name", ["..%2Fsecret.jpg", "UPPER.jpg", "a.png"])
async def test_invalid_image_names_are_rejected(client, name):
    assert (await client.get(f"/assets/menu/{name}")).status_code in {404, 422}
