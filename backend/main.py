# main.py
from contextlib import asynccontextmanager
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.init_db import init_vector_index, seed_initial_menu
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.menu import router as menu_router
from app.api.reservation import router as reservation_router
from app.api.chat import router as chat_router
from app.core.exceptions import MenuItemNotFoundException, EmbeddingServiceException, DatabaseException, ReservationNotFoundException
from fastapi import Request, status
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    
    await seed_initial_menu()
    await init_vector_index()
    
    yield
    
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

@app.exception_handler(MenuItemNotFoundException)
async def menu_item_not_found_handler(request: Request, exc: MenuItemNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc), "code": "NOT_FOUND"}
    )

@app.exception_handler(EmbeddingServiceException)
async def embedding_service_handler(request: Request, exc: EmbeddingServiceException):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": exc.detail, "code": "OLLAMA_SERVICE_ERROR"}
    )

@app.exception_handler(DatabaseException)
async def database_exception_handler(request: Request, exc: DatabaseException):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal database error.", "code": "DATABASE_ERROR"}
    )

@app.exception_handler(ReservationNotFoundException)
async def reservation_not_found_handler(request: Request, exc: ReservationNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc), "code": "NOT_FOUND"}
    )

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(menu_router, prefix=settings.API_V1_STR)
app.include_router(reservation_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "RAG-taurant API is running", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)