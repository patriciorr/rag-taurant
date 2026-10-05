# backend/app/rag/tools.py
from typing import Optional
from langchain_core.tools import tool
from pymongo import MongoClient
from app.core.config import settings
from app.rag.embeddings import embeddings_service
from app.models.menu import Allergen
from app.models.reservation import (
    ReservationContact,
    ReservationCreate,
    ReservationInDB,
    ReservationUpdate,
)
from app.service.menu import menu_service
from app.service.reservation import reservation_service
from app.service.weather import get_restaurant_weather
from app.core.exceptions import ReservationValidationException

client = MongoClient(settings.MONGODB_URI)
db = client[settings.DB_NAME]

# --- BÚSQUEDA RAG: MENÚ ---
@tool
async def search_menu(
    query: str,
    vegan_only: bool = False,
    vegetarian_only: bool = False,
    exclude_allergens: Optional[list[str]] = None,
    available_only: bool = True,
) -> str:
    """Busca platos y aplica las preferencias usando los atributos registrados de la carta."""
    items = await menu_service.list_menu()
    if not items:
        return "No hay información de platos disponible en la carta para responder."

    valid_allergens = {allergen.value for allergen in Allergen}
    excluded = set(exclude_allergens or [])
    unknown_allergens = excluded - valid_allergens
    if unknown_allergens:
        return "No pude aplicar el filtro porque contiene alérgenos no reconocidos: " + ", ".join(sorted(unknown_allergens))

    similar_items = await menu_service.search_similar_dishes(query, limit=len(items))
    items_by_id = {item.id: item for item in items}
    matches = [
        items_by_id[result["id"]]
        for result in similar_items
        if result.get("id") in items_by_id
    ]

    matches = [
        item
        for item in matches
        if (not vegan_only or item.is_vegan)
        and (not vegetarian_only or item.is_vegetarian)
        and (not available_only or item.available)
        and not excluded.intersection(allergen.value for allergen in item.allergens)
    ]
    if not matches:
        return "No encontré platos disponibles que coincidan con la consulta y los filtros indicados."

    response = ["Coincidencias recuperadas de la carta:"]
    for item in matches:
        allergens = ", ".join(allergen.value for allergen in item.allergens) or "ninguno registrado"
        response.append(
            f"- {item.name} ({item.price:.2f}€). {item.description} "
            f"Alérgenos registrados: {allergens}. "
            f"Vegano: {'sí' if item.is_vegan else 'no'}; "
            f"vegetariano: {'sí' if item.is_vegetarian else 'no'}; "
            f"disponibilidad: {'disponible' if item.available else 'no disponible'}. "
            "La carta no indica datos sobre contaminación cruzada, por lo que no se puede garantizar "
            "que un plato sea seguro para una alergia."
        )
    return "\n".join(response)

# --- BÚSQUEDA RAG: INFORMACIÓN GENERAL (llm.txt) ---
@tool
def search_info(query: str) -> str:
    """Busca información institucional del restaurante: ubicación, horarios, políticas de terraza, aparcamiento o normas."""
    query_vector = embeddings_service.embed_query(query)
    
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 10,
                "limit": 3
            }
        },
        {"$project": {"_id": 0, "embedding": 0}}
    ]
    
    results = list(db["knowledge"].aggregate(pipeline))
    if not results:
        return "No se encontró información institucional sobre esa consulta."
    
    response = "Información del restaurante:\n"
    for info in results:
        response += f"- {info.get('content')}\n"
    return response

# --- CRUD RESERVAS ---

def prepare_table_reservation(arguments: dict[str, object]) -> ReservationCreate:
    return ReservationCreate(**arguments)


def format_reservation_confirmation(reservation: ReservationCreate) -> str:
    return (
        "Revisa los datos de la reserva que se enviarán al servicio:\n"
        f"- Nombre: {reservation.customer_name}\n"
        f"- Email: {reservation.email}\n"
        f"- Teléfono: {reservation.phone}\n"
        f"- Fecha: {reservation.date.isoformat()}\n"
        f"- Hora: {reservation.time.isoformat(timespec='minutes')}\n"
        f"- Comensales: {reservation.guests}\n"
        "Todavía no se ha creado. Responde «sí» para confirmar o «no» para descartarla."
    )


@tool
async def make_table_reservation(
    customer_name: str,
    email: str,
    phone: str,
    date: str,
    time: str,
    guests: int,
) -> str:
    """Prepara una reserva con nombre, email, teléfono, fecha, hora y comensales; no la registra."""
    reservation = prepare_table_reservation(
        {
            "customer_name": customer_name,
            "email": email,
            "phone": phone,
            "date": date,
            "time": time,
            "guests": guests,
        }
    )
    return format_reservation_confirmation(reservation)

async def get_verified_table_reservation(
    reservation_id: str,
    email: str,
    phone: str,
) -> ReservationInDB:
    contact = ReservationContact(email=email, phone=phone)
    return await reservation_service.get_reservation(reservation_id, contact)


def format_verified_table_reservation(reservation: ReservationInDB) -> str:
    status = "activa" if reservation.status == "confirmed" else "cancelada"
    return (
        f"Reserva verificada ({status}): {reservation.reservation_id}.\n"
        f"- Cliente: {reservation.customer_name}\n"
        f"- Fecha: {reservation.date.isoformat()} a las "
        f"{reservation.time.isoformat(timespec='minutes')}\n"
        f"- Comensales: {reservation.guests}"
    )


@tool
async def get_table_reservation(reservation_id: str, email: str, phone: str) -> str:
    """Consulta una reserva verificando su código, correo electrónico y teléfono."""
    reservation = await get_verified_table_reservation(reservation_id, email, phone)
    return format_verified_table_reservation(reservation)


@tool
def get_weather_forecast(date: Optional[str] = None) -> str:
    """Consulta la previsión meteorológica del restaurante. Indica date en formato YYYY-MM-DD para una fecha concreta; omítela para consultar el horizonte disponible."""
    return get_restaurant_weather(date)


async def prepare_table_reservation_update(
    reservation_id: str,
    email: str,
    phone: str,
    date: Optional[str] = None,
    time: Optional[str] = None,
    guests: Optional[int] = None,
) -> tuple[ReservationInDB, ReservationUpdate]:
    contact = ReservationContact(email=email, phone=phone)
    reservation = await reservation_service.get_reservation(reservation_id, contact)
    if reservation.status != "confirmed":
        raise ReservationValidationException("Cancelled reservations cannot be modified.")

    update_fields = {
        key: value
        for key, value in {"date": date, "time": time, "guests": guests}.items()
        if value is not None
    }
    update = ReservationUpdate(**update_fields)
    ReservationCreate(
        customer_name=reservation.customer_name,
        email=reservation.email,
        phone=reservation.phone,
        date=update.date or reservation.date,
        time=update.time or reservation.time,
        guests=update.guests or reservation.guests,
    )
    return reservation, update


def format_table_reservation_update(
    reservation: ReservationInDB,
    update: ReservationUpdate,
) -> str:
    changes = []
    for field, label in (
        ("date", "Fecha"),
        ("time", "Hora"),
        ("guests", "Comensales"),
    ):
        value = getattr(update, field)
        if field not in update.model_fields_set:
            continue
        if field == "date":
            value = value.isoformat()
            previous = reservation.date.isoformat()
        elif field == "time":
            value = value.isoformat(timespec="minutes")
            previous = reservation.time.isoformat(timespec="minutes")
        else:
            previous = str(reservation.guests)
            value = str(value)
        changes.append(f"- {label}: {previous} → {value}")

    return (
        f"Revisa los cambios para la reserva '{reservation.reservation_id}':\n"
        + "\n".join(changes)
        + "\nTodavía no se ha modificado. Responde «sí» para confirmar o «no» para descartar."
    )


@tool
async def edit_table_reservation(
    reservation_id: str,
    email: str,
    phone: str,
    date: Optional[str] = None,
    time: Optional[str] = None,
    guests: Optional[int] = None,
) -> str:
    """Prepara cambios de fecha, hora o comensales tras verificar el código, email y teléfono; no modifica la reserva."""
    reservation, update = await prepare_table_reservation_update(
        reservation_id=reservation_id,
        email=email,
        phone=phone,
        date=date,
        time=time,
        guests=guests,
    )
    return format_table_reservation_update(reservation, update)

@tool
async def delete_table_reservation(reservation_id: str, email: str, phone: str) -> str:
    """Prepara la cancelación tras verificar el código, email y teléfono. No cancela hasta confirmación explícita."""
    contact = ReservationContact(email=email, phone=phone)
    reservation = await reservation_service.get_reservation(reservation_id, contact)
    if reservation.status == "cancelled":
        return f"La reserva '{reservation.reservation_id}' ya está cancelada."

    return (
        f"Reserva '{reservation.reservation_id}' a nombre de {reservation.customer_name}, "
        f"para el {reservation.date.isoformat()} a las {reservation.time.isoformat(timespec='minutes')} "
        f"({reservation.guests} comensales). No la canceles todavía; presenta este resumen y espera "
        "una confirmación afirmativa explícita del cliente."
    )

# Exportar conjunto de herramientas para el agente
bot_tools = [
    search_menu,
    search_info,
    get_weather_forecast,
    make_table_reservation,
    get_table_reservation,
    edit_table_reservation,
    delete_table_reservation
]