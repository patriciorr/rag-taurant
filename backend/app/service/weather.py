# app/services/weather.py
import requests
#from app.core.config import settings

def get_restaurant_weather() -> str:
    """Consults the real-time weather forecast at the restaurant's coordinates."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"forecast_days=14&"
            f"latitude={37.3828}&longitude={-5.9732}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max&timezone=auto"
        )

        # Example API call for reference:
        # https://api.open-meteo.com/v1/forecast?latitude=37.3828&longitude=-5.9732&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max&timezone=auto
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json().get("daily", {})
        
        temp_max = data.get("temperature_2m_max", ["N/D"])
        temp_min = data.get("temperature_2m_min", ["N/D"])
        precip = data.get("precipitation_probability_max", ["N/D"])
        wind = data.get("wind_speed_10m_max", ["N/D"])
        forecast_days = data.get("time", ["N/D"])
        
        return (
            f"El tiempo actual en la ubicación del restaurante: "
            f"Día: {forecast_days[0]} - Temperatura máxima: {temp_max[0]}°C - Temperatura mínima: {temp_min[0]}°C - Probabilidad de precipitación: {precip[0]}% - Viento: {wind[0]} km/h."
            f"El tiempo en los próximos días: "
            f"Día: {forecast_days[1]} - Temperatura máxima: {temp_max[1]}°C - Temperatura mínima: {temp_min[1]}°C - Probabilidad de precipitación: {precip[1]}% - Viento: {wind[1]} km/h."
            f"Día: {forecast_days[2]} - Temperatura máxima: {temp_max[2]}°C - Temperatura mínima: {temp_min[2]}°C - Probabilidad de precipitación: {precip[2]}% - Viento: {wind[2]} km/h."
            f"Día: {forecast_days[3]} - Temperatura máxima: {temp_max[3]}°C - Temperatura mínima: {temp_min[3]}°C - Probabilidad de precipitación: {precip[3]}% - Viento: {wind[3]} km/h."
            f"Día: {forecast_days[4]} - Temperatura máxima: {temp_max[4]}°C - Temperatura mínima: {temp_min[4]}°C - Probabilidad de precipitación: {precip[4]}% - Viento: {wind[4]} km/h."
            f"Día: {forecast_days[5]} - Temperatura máxima: {temp_max[5]}°C - Temperatura mínima: {temp_min[5]}°C - Probabilidad de precipitación: {precip[5]}% - Viento: {wind[5]} km/h."
            f"Día: {forecast_days[6]} - Temperatura máxima: {temp_max[6]}°C - Temperatura mínima: {temp_min[6]}°C - Probabilidad de precipitación: {precip[6]}% - Viento: {wind[6]} km/h."
        )
    except Exception as e:
        return f"No se pudo obtener el clima en tiempo real. Detalle: {str(e)}"