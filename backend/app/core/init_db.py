# app/core/init_db.py
from app.core.database import db_instance
from app.rag.embeddings import get_embeddings_batch
from app.core.config import settings
from app.evaluation.embedding_migration import (
    VECTOR_INDEX_NAME,
    get_vector_index_dimensions,
    vector_index_definition,
)
from app.service.menu import menu_embedding_text

INITIAL_MENU = [
  {
    "name": "Gazpacho Andaluz Tradicional",
    "description": "Sopa fría de tomates maduros, pimiento, pepino y aceite de oliva virgen extra.",
    "price": 8.5,
    "category": "entrante",
    "allergens": [],
    "is_vegan": True,
    "is_vegetarian": True,
    "available": True,
    "id": "1"
  },
  {
    "name": "Croquetas de Jamón Ibérico",
    "description": "Croquetas cremosas elaboradas con bechamel casera y jamón de bellota 100% ibérico.",
    "price": 12.0,
    "category": "entrante",
    "allergens": [
      "gluten",
      "lácteos",
      "huevo"
    ],
    "is_vegan": False,
    "is_vegetarian": False,
    "available": True,
    "id": "2"
  },
  {
    "name": "Paella de Mariscos del Señorito",
    "description": "Arroz bomba cocinado a fuego lento con gambas peladas, calamares y mejillones sin cáscara.",
    "price": 21.0,
    "category": "principal",
    "allergens": [
      "crustáceos",
      "pescado"
    ],
    "is_vegan": False,
    "is_vegetarian": False,
    "available": True,
    "id": "3"
  },
  {
    "name": "Hamburguesa Vegana de Garbanzos y Espinacas",
    "description": "Medallón casero servido en pan artesanal con aguacate, tomate y mayonesa vegana de ajo.",
    "price": 14.5,
    "category": "principal",
    "allergens": [
      "gluten",
      "soja"
    ],
    "is_vegan": True,
    "is_vegetarian": True,
    "available": True,
    "id": "4"
  },
  {
    "name": "Tarta de Queso Cremosita San Sebastián",
    "description": "Tarta horneada al estilo vasco, tostada por fuera y fluida en el centro.",
    "price": 7.0,
    "category": "postre",
    "allergens": [
      "lácteos",
      "huevo"
    ],
    "is_vegan": False,
    "is_vegetarian": True,
    "available": True,
    "id": "5"
  }
]

async def init_vector_index():
    """Creates the vector search index on the 'menu' collection."""
    collection_names = set(await db_instance.db.list_collection_names())
    target_collections = ["menu"]
    if "knowledge" in collection_names:
        target_collections.append("knowledge")

    for collection_name in target_collections:
        collection = db_instance.db[collection_name]
        indexes = await (await collection.list_search_indexes()).to_list(length=None)
        existing = next(
            (index for index in indexes if index.get("name") == VECTOR_INDEX_NAME),
            None,
        )
        if existing is None:
            await db_instance.db.command(
                "createSearchIndexes",
                collection_name,
                indexes=[
                    {
                        "name": VECTOR_INDEX_NAME,
                        "type": "vectorSearch",
                        "definition": vector_index_definition(
                            settings.EMBEDDING_DIMENSIONS
                        ),
                    }
                ],
            )
            continue
        actual_dimensions = get_vector_index_dimensions(existing)
        if actual_dimensions != settings.EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Vector index {VECTOR_INDEX_NAME!r} on {collection_name!r} has "
                f"{actual_dimensions!r} dimensions; the configured embedding "
                f"model {settings.EMBEDDING_MODEL!r} returns "
                f"{settings.EMBEDDING_DIMENSIONS}. Run "
                "'python scripts/reindex_embeddings.py' before starting the backend."
            )

async def seed_initial_menu():
    """Seeds the database with the initial menu calculating embeddings in batch."""
    collection = db_instance.db["menu"]
    count = await collection.count_documents({})
    
    if count > 0:
        print("The menu already contains data. Skipping initial seeding.")
        return

    print("Inserting initial dishes and generating embeddings in batch...")
    
    texts = [menu_embedding_text(item) for item in INITIAL_MENU]
    
    vectors = await get_embeddings_batch(texts)
    
    for item, vector in zip(INITIAL_MENU, vectors):
        item["embedding"] = vector

    await collection.insert_many(INITIAL_MENU)
    print(f"Inserted {len(INITIAL_MENU)} initial dishes.")