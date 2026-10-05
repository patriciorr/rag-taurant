import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.core.database import db_instance
from app.repository.reservation import reservation_repository
from main import app


@pytest.fixture
async def mongo_api_client():
    uri = os.getenv("TEST_MONGODB_URI", "mongodb://localhost:27017/?directConnection=true")
    database_name = f"rag_taurant_test_{uuid4().hex}"
    mongo_client = AsyncMongoClient(uri, serverSelectionTimeoutMS=3000)
    try:
        await mongo_client.admin.command("ping")
    except Exception:
        await mongo_client.close()
        raise

    previous_client = db_instance.client
    previous_database = db_instance.db
    db_instance.client = mongo_client
    db_instance.db = mongo_client[database_name]

    try:
        await reservation_repository.ensure_indexes()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        await mongo_client.drop_database(database_name)
        await mongo_client.close()
        db_instance.client = previous_client
        db_instance.db = previous_database