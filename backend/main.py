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
from app.core.exceptions import (
    DatabaseException,
    EmbeddingServiceException,
    MenuItemNotFoundException,
    ReservationConflictException,
    ReservationNotFoundException,
    ReservationValidationException,
)
from app.repository.reservation import reservation_repository
from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await reservation_repository.ensure_indexes()
    
    await seed_initial_menu()
    await init_vector_index()
    
    yield
    
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

def uses_shared_api_errors(request: Request) -> bool:
    path = request.url.path
    return path.startswith(f"{settings.API_V1_STR}/menu") or path.startswith(f"{settings.API_V1_STR}/reservations")

@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    if uses_shared_api_errors(request):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": errors, "code": "VALIDATION_ERROR"},
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(exc.errors())},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if not uses_shared_api_errors(request):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": jsonable_encoder(exc.detail)},
            headers=exc.headers,
        )

    codes = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": jsonable_encoder(exc.detail), "code": codes.get(exc.status_code, "HTTP_ERROR")},
        headers=exc.headers,
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
        content={"detail": "Menu search service unavailable.", "code": "EMBEDDING_SERVICE_ERROR"}
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
        content={"detail": "Reservation not found.", "code": "NOT_FOUND"}
    )

@app.exception_handler(ReservationConflictException)
async def reservation_conflict_handler(request: Request, exc: ReservationConflictException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": "A reservation already exists for one of these contacts on this date.",
            "code": "RESERVATION_CONFLICT",
        },
    )

@app.exception_handler(ReservationValidationException)
async def reservation_validation_handler(request: Request, exc: ReservationValidationException):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(exc), "code": "VALIDATION_ERROR"},
    )

@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    if uses_shared_api_errors(request):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error.", "code": "INTERNAL_SERVER_ERROR"},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"},
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