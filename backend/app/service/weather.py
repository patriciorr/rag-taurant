import logging
import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

FORECAST_UNAVAILABLE = (
    "No pude consultar la previsión meteorológica ahora. Inténtalo de nuevo más tarde."
)
FORECAST_INCOMPLETE = (
    "La previsión meteorológica no está disponible temporalmente para todas las fechas solicitadas."
)

DAILY_FIELDS = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "wind_speed_10m_max",
)
FIELD_LABELS = (
    ("temperature_2m_max", "máxima", "°C"),
    ("temperature_2m_min", "mínima", "°C"),
    ("precipitation_probability_max", "probabilidad de precipitación", "%"),
    ("wind_speed_10m_max", "viento máximo", "km/h"),
)


def _number(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def get_restaurant_weather(
    requested_date: str | None = None,
    *,
    today: date | None = None,
) -> str:
    if requested_date is not None:
        try:
            parsed_date = date.fromisoformat(requested_date)
        except (TypeError, ValueError):
            return "Indícame una fecha válida en formato YYYY-MM-DD."
        if parsed_date.isoformat() != requested_date:
            return "Indícame una fecha válida en formato YYYY-MM-DD."
    else:
        parsed_date = None

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": settings.RESTAURANT_LAT,
                "longitude": settings.RESTAURANT_LON,
                "daily": ",".join(DAILY_FIELDS),
                "forecast_days": 14,
                "timezone": "auto",
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("Open-Meteo forecast request failed.")
        return FORECAST_UNAVAILABLE

    if not isinstance(data, dict) or not isinstance(data.get("daily"), dict):
        logger.warning("Open-Meteo returned an incomplete forecast response.")
        return FORECAST_INCOMPLETE

    daily = data["daily"]
    days = daily.get("time")
    values = {field: daily.get(field) for field in DAILY_FIELDS}
    if (
        not isinstance(days, list)
        or len(days) != 14
        or any(not isinstance(day, str) for day in days)
        or any(not isinstance(items, list) or len(items) != 14 for items in values.values())
        or any(not _number(value) for items in values.values() for value in items)
    ):
        logger.warning("Open-Meteo returned an incomplete 14-day forecast.")
        return FORECAST_INCOMPLETE

    try:
        forecast_dates = [date.fromisoformat(day) for day in days]
        if any(parsed.isoformat() != original for parsed, original in zip(forecast_dates, days)):
            raise ValueError("Forecast date is not in ISO format.")
        timezone = data.get("timezone")
        if not isinstance(timezone, str):
            raise ValueError("Forecast timezone is missing.")
        forecast_today = today or datetime.now(ZoneInfo(timezone)).date()
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        logger.warning("Open-Meteo returned invalid dates or timezone metadata.")
        return FORECAST_INCOMPLETE

    expected_dates = [forecast_today + timedelta(days=offset) for offset in range(14)]
    if forecast_dates != expected_dates:
        logger.warning("Open-Meteo forecast does not cover the expected 14-day horizon.")
        return FORECAST_INCOMPLETE

    if parsed_date is not None:
        if parsed_date not in forecast_dates:
            return (
                f"No hay previsión disponible para {parsed_date.isoformat()}. "
                f"El horizonte disponible es del {forecast_dates[0].isoformat()} "
                f"al {forecast_dates[-1].isoformat()}."
            )
        indices = [forecast_dates.index(parsed_date)]
    else:
        indices = list(range(14))

    forecast_lines = []
    for index in indices:
        details = [
            f"{label}: {values[field][index]:g}{unit}"
            for field, label, unit in FIELD_LABELS
        ]
        forecast_lines.append(f"{days[index]}: " + "; ".join(details) + ".")
    return "Previsión meteorológica para la ubicación del restaurante:\n" + "\n".join(
        forecast_lines
    )
