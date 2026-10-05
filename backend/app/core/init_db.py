from app.core.config import settings
from app.core.database import db_instance
from app.evaluation.embedding_migration import (
    VECTOR_INDEX_NAME,
    get_vector_index_dimensions,
    vector_index_definition,
)
from app.rag.embeddings import get_embeddings_batch
from app.service.menu import menu_embedding_text

INITIAL_MENU = [
    {
        "id": "1",
        "name": "Gazpacho andaluz",
        "description": "Tomate maduro, pepino, pimiento y aceite de oliva virgen extra, servido bien frío.",
        "price": 8.5,
        "category": "entrante",
        "allergens": ["apio", "sulfitos"],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/gazpacho.jpg",
    },
    {
        "id": "2",
        "name": "Berenjenas con miel de caña",
        "description": "Berenjena crujiente, miel de caña de Frigiliana y sal en escamas.",
        "price": 14.0,
        "category": "entrante",
        "allergens": ["gluten"],
        "is_vegan": False,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/berenjenas.jpg",
    },
    {
        "id": "3",
        "name": "Croquetas de jamón ibérico",
        "description": "Bechamel sedosa, jamón ibérico y un rebozado dorado hecho al momento.",
        "price": 12.0,
        "category": "entrante",
        "allergens": ["gluten", "lácteos", "huevo"],
        "is_vegan": False,
        "is_vegetarian": False,
        "available": True,
        "image_url": "/assets/menu/croquetas.jpg",
    },
    {
        "id": "4",
        "name": "Tortillitas de camarones",
        "description": "Finas y crujientes, con camarones, perejil fresco y harina de garbanzo.",
        "price": 13.5,
        "category": "entrante",
        "allergens": ["crustáceos", "gluten", "huevo"],
        "is_vegan": False,
        "is_vegetarian": False,
        "available": True,
        "image_url": "/assets/menu/tortillitas.jpg",
    },
    {
        "id": "5",
        "name": "Arroz marinero de Huelva",
        "description": "Arroz bomba meloso con pescado de lonja, mejillones y gambas.",
        "price": 22.0,
        "category": "principal",
        "allergens": ["crustáceos", "pescado", "moluscos"],
        "is_vegan": False,
        "is_vegetarian": False,
        "available": True,
        "image_url": "/assets/menu/arroz-marinero.jpg",
    },
    {
        "id": "6",
        "name": "Pisto de la huerta con huevo",
        "description": "Tomate, calabacín, berenjena y pimiento cocinados despacio, con huevo campero.",
        "price": 15.0,
        "category": "principal",
        "allergens": ["huevo"],
        "is_vegan": False,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/pisto.jpg",
    },
    {
        "id": "7",
        "name": "Espinacas con garbanzos",
        "description": "Garbanzos tiernos y espinacas de temporada con ajo, comino y un toque de pimentón.",
        "price": 11.0,
        "category": "principal",
        "allergens": ["apio"],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/espinacas-garbanzos.jpg",
    },
    {
        "id": "8",
        "name": "Ensalada de naranja, aceituna y almendra",
        "description": "Naranjas de temporada, aceituna aloreña, cebolla dulce y almendra tostada.",
        "price": 13.0,
        "category": "principal",
        "allergens": ["frutos secos"],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/ensalada-naranja.jpg",
    },
    {
        "id": "9",
        "name": "Garbanzos con altramuces",
        "description": "Guiso vegetal de garbanzos, altramuces y verduras con hierbabuena.",
        "price": 15.5,
        "category": "principal",
        "allergens": ["altramuces"],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/garbanzos-altramuces.jpg",
    },
    {
        "id": "10",
        "name": "Ensalada templada con vinagreta de cacahuete",
        "description": "Verduras de temporada, hojas tiernas y una vinagreta de cacahuete, mostaza y sésamo.",
        "price": 16.0,
        "category": "principal",
        "allergens": ["cacahuete", "mostaza", "sésamo"],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/ensalada-templada.jpg",
    },
    {
        "id": "11",
        "name": "Tarta de almendra de la abuela",
        "description": "Bizcocho húmedo de almendra tostada, huevo campero y crema ligera.",
        "price": 7.5,
        "category": "postre",
        "allergens": ["huevo", "lácteos", "frutos secos"],
        "is_vegan": False,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/tarta-almendra.jpg",
    },
    {
        "id": "12",
        "name": "Mousse de chocolate y naranja",
        "description": "Chocolate negro, naranja sevillana y crema vegetal, servidos con cacao.",
        "price": 7.0,
        "category": "postre",
        "allergens": ["soja"],
        "is_vegan": True,
        "is_vegetarian": True,
        "available": True,
        "image_url": "/assets/menu/mousse-chocolate.jpg",
    },
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
    """Upserts only the curated catalog records, retaining all other menu data."""
    collection = db_instance.db["menu"]
    seeded_ids = [item["id"] for item in INITIAL_MENU]
    existing_items = await collection.find({"id": {"$in": seeded_ids}}).to_list(
        length=None
    )
    existing_by_id = {item["id"]: item for item in existing_items}
    fields = tuple(INITIAL_MENU[0])
    changed_items = [
        item
        for item in INITIAL_MENU
        if item["id"] not in existing_by_id
        or not existing_by_id[item["id"]].get("embedding")
        or any(existing_by_id[item["id"]].get(field) != item[field] for field in fields)
    ]

    if not changed_items:
        print("The curated menu is already up to date.")
        return

    print(f"Updating {len(changed_items)} curated dishes and generating embeddings...")
    vectors = await get_embeddings_batch(
        [menu_embedding_text(item) for item in changed_items]
    )
    for item, vector in zip(changed_items, vectors):
        await collection.update_one(
            {"id": item["id"]},
            {"$set": {**item, "embedding": vector}},
            upsert=True,
        )
    print(f"Upserted {len(changed_items)} curated dishes.")
