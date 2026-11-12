import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api import chat
from app.core import rate_limit
from app.core.config import Settings
from app.rag import vector_search


def make_request(forwarded: str | None = None, host: str = "10.0.0.9") -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (host, 1234)})


def test_production_requires_secrets():
    with pytest.raises(ValueError, match="MENU_ADMIN_TOKEN"):
        Settings(_env_file=None, ENVIRONMENT="production", GOOGLE_API_KEY="key")
    Settings(_env_file=None, ENVIRONMENT="production", GOOGLE_API_KEY="k", MENU_ADMIN_TOKEN="t")


def test_client_ip_ignores_spoofed_leading_entries(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "TRUSTED_PROXY_COUNT", 2)
    request = make_request("6.6.6.6, 1.2.3.4, 172.16.0.1")
    assert rate_limit.client_ip(request) == "1.2.3.4"


def test_chat_rate_limit_per_ip_and_global(monkeypatch):
    rate_limit.chat_limiter.clear()
    monkeypatch.setattr(rate_limit.settings, "CHAT_RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(rate_limit.settings, "CHAT_GLOBAL_DAILY_LIMIT", 3)
    first, second = make_request("1.1.1.1"), make_request("2.2.2.2")
    rate_limit.enforce_chat_rate_limit(first)
    rate_limit.enforce_chat_rate_limit(first)
    with pytest.raises(HTTPException) as exc:
        rate_limit.enforce_chat_rate_limit(first)
    assert exc.value.status_code == 429
    rate_limit.enforce_chat_rate_limit(second)
    with pytest.raises(HTTPException):
        rate_limit.enforce_chat_rate_limit(make_request("3.3.3.3"))
    rate_limit.chat_limiter.clear()


def test_chat_message_length_is_capped():
    with pytest.raises(ValueError):
        chat.ChatRequest(message="x" * 501, session_id="s")


@pytest.mark.asyncio
async def test_local_vector_search_ranks_by_cosine(monkeypatch):
    docs = [
        {"id": "far", "embedding": [0.0, 1.0], "embedding_model": "m"},
        {"id": "near", "embedding": [1.0, 0.1], "embedding_model": "m"},
    ]

    class Cursor:
        async def to_list(self, length):
            return docs

    class Collection:
        def find(self, query, projection):
            return Cursor()

    monkeypatch.setattr(vector_search.settings, "VECTOR_SEARCH_MODE", "local")
    monkeypatch.setattr(vector_search.db_instance, "db", {"menu": Collection()})

    results = await vector_search.vector_search("menu", [1.0, 0.0], 1)

    assert [r["id"] for r in results] == ["near"]
    assert "embedding" not in results[0] and "embedding_model" not in results[0]
    assert results[0]["score"] > 0.9
