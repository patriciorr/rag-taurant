# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.menu import router as menu_router, _load_dishes_from_file
from app.rag.vectorstore import vector_store
from app.api.chat import router as chat_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Configuración de CORS para conectar con React (Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(menu_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def startup_event():
    """Al iniciar la app, asegura que todos los platos en JSON estén indexados en ChromaDB."""
    dishes = _load_dishes_from_file()
    for dish in dishes:
        vector_store.upsert_dish(dish)
    print(f"✅ Se han sincronizado {len(dishes)} platos en ChromaDB.")

@app.get("/")
def root():
    return {"message": "Servidor del Restaurante RAG activo", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)