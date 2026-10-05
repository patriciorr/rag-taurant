# backend/app/rag/tools.py
import uuid
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool
from pymongo import MongoClient
from langchain_ollama import OllamaEmbeddings
from app.core.config import settings
from app.models.menu import Allergen
from app.models.reservation import ReservationContact, ReservationCreate, ReservationUpdate, ReservationInDB
from app.service.menu import menu_service
from app.service.reservation import reservation_service
from app.service.weather import get_restaurant_weather

client = MongoClient(settings.MONGODB_URI)
db = client[settings.DB_NAME]

embeddings_model = OllamaEmbeddings(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.EMBEDDING_MODEL
)

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
    query_vector = embeddings_model.embed_query(query)
    
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

def _find_reservation(identifier: str) -> Optional[dict]:
    """Busca una reserva por reservation_id, email o número de teléfono."""
    query = {
        "$or": [
            {"reservation_id": identifier},
            {"email": identifier.lower().strip()},
            {"phone": identifier.strip()}
        ]
    }
    return db["reservations"].find_one(query, {"_id": 0})

@tool
def make_table_reservation(customer_name: str, email: str, phone: str, date: str, time: str, guests: int) -> str:
    """Crea una nueva reserva de mesa. Requiere nombre, email, teléfono, fecha (YYYY-MM-DD), hora (HH:MM) y número de personas."""
    try:
        raw_data = {
            "customer_name": customer_name,
            "email": email.lower().strip(),
            "phone": phone.strip(),
            "date": date,
            "time": time,
            "guests": guests
        }
        validated_data = ReservationCreate(**raw_data)
        
        reservation_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        reservation_db = ReservationInDB(
            **validated_data.model_dump(),
            reservation_id=reservation_id,
            created_at=datetime.utcnow(),
            status="confirmed"
        )
        
        db["reservations"].insert_one(reservation_db.model_dump())
        return f"✅ Reserva confirmada con éxito. Código de reserva: {reservation_id} a nombre de {validated_data.customer_name}."
    except Exception as e:
        return f"❌ Error de validación al crear la reserva: {str(e)}"

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


@tool
def edit_table_reservation(
    identifier: str, 
    date: Optional[str] = None, 
    time: Optional[str] = None, 
    guests: Optional[int] = None,
    customer_name: Optional[str] = None
) -> str:
    """Edita los datos de una reserva existente buscándola por ID, email o teléfono."""
    reservation = _find_reservation(identifier)
    if not reservation:
        return f"No se encontró ninguna reserva para modificar con el identificador '{identifier}'."
    
    update_fields = {}
    if date: update_fields["date"] = date
    if time: update_fields["time"] = time
    if guests: update_fields["guests"] = guests
    if customer_name: update_fields["customer_name"] = customer_name
    
    if not update_fields:
        return "No se especificaron campos para actualizar."
        
    try:
        validated_update = ReservationUpdate(**update_fields)
        changes = {k: v for k, v in validated_update.model_dump().items() if v is not None}
        
        db["reservations"].update_one(
            {"reservation_id": reservation["reservation_id"]},
            {"$set": changes}
        )
        return f"✅ Reserva '{reservation['reservation_id']}' actualizada correctamente con los nuevos datos: {changes}."
    except Exception as e:
        return f"❌ Error de validación al editar la reserva: {str(e)}"

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