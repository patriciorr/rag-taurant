# app/services/weather.py
import requests
from app.core.config import settings

def get_restaurant_weather() -> str:
    """Consulta el pronóstico meteorológico real en las coordenadas del restaurante."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={settings.RESTAURANT_LAT}&longitude={settings.RESTAURANT_LON}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
        )
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json().get("current", {})
        
        temp = data.get("temperature_2m", "N/D")
        wind = data.get("wind_speed_10m", "N/D")
        humidity = data.get("relative_humidity_2m", "N/D")
        
        return (
            f"El tiempo actual en la ubicación del restaurante: "
            f"Temperatura: {temp}°C, Humedad: {humidity}%, Viento: {wind} km/h."
        )
    except Exception as e:
        return f"No se pudo obtener el clima en tiempo real. Detalle: {str(e)}"