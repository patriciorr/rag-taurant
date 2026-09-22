# app/core/database.py
from pymongo import AsyncMongoClient
from app.core.config import settings

class Database:
    client: AsyncMongoClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    db_instance.client = AsyncMongoClient(settings.MONGODB_URI)
    db_instance.db = db_instance.client[settings.DB_NAME]
    print("Async connection with PyMongo established.")

async def close_mongo_connection():
    if db_instance.client:
        await db_instance.client.close()
        print("Async connection with PyMongo closed.")