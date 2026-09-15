# app/rag/vectorstore.py
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.core.config import settings
from app.models.menu import MenuItem
from typing import List, Optional

class VectorStoreManager:
    def __init__(self):
        # 1. Cliente persistente de ChromaDB en local
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(allow_reset=True)
        )
        # 2. Embeddings multilingües locales
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
        
        # 3. Colección del Menú
        self.menu_collection = self.client.get_or_create_collection(
            name="restaurant_menu",
            metadata={"description": "Platos y carta del restaurante para RAG"}
        )

    def upsert_dish(self, dish: MenuItem):
        """Sincroniza un plato en ChromaDB (crea o actualiza su vector)."""
        text_content = dish.to_rag_text()
        embedding = self.embeddings_model.embed_query(text_content)
        
        metadata = {
            "name": dish.name,
            "category": dish.category.value,
            "price": float(dish.price),
            "is_vegan": dish.is_vegan,
            "is_vegetarian": dish.is_vegetarian,
            "available": dish.available
        }

        self.menu_collection.upsert(
            ids=[dish.id],
            embeddings=[embedding],
            documents=[text_content],
            metadatas=[metadata]
        )

    def delete_dish(self, dish_id: str):
        """Elimina el vector correspondiente a un plato."""
        self.menu_collection.delete(ids=[dish_id])

    def search_similar_dishes(self, query: str, n_results: int = 3) -> List[dict]:
        """Realiza una búsqueda por similitud vectorial."""
        query_embedding = self.embeddings_model.embed_query(query)
        results = self.menu_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        items = []
        if results and results["documents"]:
            for doc, meta, id_ in zip(results["documents"][0], results["metadatas"][0], results["ids"][0]):
                items.append({
                    "id": id_,
                    "content": doc,
                    "metadata": meta
                })
        return items

# Singleton para reutilizar la conexión
vector_store = VectorStoreManager()