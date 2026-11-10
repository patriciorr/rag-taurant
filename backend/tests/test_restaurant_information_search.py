import pytest

from app.rag import tools


@pytest.mark.asyncio
async def test_search_info_uses_shared_database_and_async_embedding(monkeypatch):
    class Cursor:
        async def to_list(self, length):
            return [{"content": "Información del pueblo."}]

    class Collection:
        async def aggregate(self, pipeline):
            assert pipeline[0]["$vectorSearch"]["queryVector"] == [0.1, 0.2]
            return Cursor()

    class Database:
        def __getitem__(self, name):
            assert name == "knowledge"
            return Collection()

    async def embed(query):
        assert query == "el pueblo"
        return [0.1, 0.2]

    monkeypatch.setattr(tools.db_instance, "db", Database())
    monkeypatch.setattr(tools, "get_embedding", embed)

    result = await tools.search_info.ainvoke({"query": "el pueblo"})

    assert "Información del pueblo." in result
