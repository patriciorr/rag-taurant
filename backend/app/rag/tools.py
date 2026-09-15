# app/rag/tools.py
from langchain_core.tools import tool
from app.rag.vectorstore import vector_store
from app.services.weather import get_restaurant_weather
from app.services.reservation import create_reservation

@tool
def search_menu_and_info(query: str) -> str:
    """
    Consulta la carta, platos, alérgenos, precios u horarios del restaurante en la base vectorial.
    Usa esta herramienta cuando el usuario pregunte sobre qué comer, precios, ingredientes o alérgenos.
    """
    results = vector_store.search_similar_dishes(query, n_results=3)
    if not results:
        return "No se encontraron platos o información coincidente en el menú."
    
    formatted = []
    for r in results:
        formatted.append(f"- {r['content']}")
    return "\n\n".join(formatted)

@tool
def get_weather_forecast() -> str:
    """
    Consulta el estado del tiempo y temperatura en el restaurante para orientar al usuario sobre su visita.
    """
    return get_restaurant_weather()

@tool
def make_table_reservation(customer_name: str, phone: str, date_time: str, guests: int) -> str:
    """
    Crea y confirma una reserva de mesa en el restaurante.
    Requiere: nombre del cliente, teléfono de contacto, fecha/hora deseada y número de comensales.
    """
    res = create_reservation(customer_name, phone, date_time, guests)
    return (
        f"✅ Reserva confirmada. Código: {res['code']} | "
        f"Titular: {res['customer_name']} | Fecha/Hora: {res['date_time']} | "
        f"Comensales: {res['guests']} personas."
    )

bot_tools = [search_menu_and_info, get_weather_forecast, make_table_reservation]