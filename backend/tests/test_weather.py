from datetime import date, timedelta
from types import SimpleNamespace

import pytest
import requests

from app.service import weather


def forecast_payload(today: date) -> dict:
    days = [(today + timedelta(days=offset)).isoformat() for offset in range(14)]
    return {
        "timezone": "Europe/Madrid",
        "daily": {
            "time": days,
            "temperature_2m_max": [20 + offset for offset in range(14)],
            "temperature_2m_min": [10 + offset for offset in range(14)],
            "precipitation_probability_max": [offset for offset in range(14)],
            "wind_speed_10m_max": [5 + offset for offset in range(14)],
        },
    }


def stub_open_meteo(monkeypatch, payload, observed):
    def get(url, *, params, timeout):
        observed.update({"url": url, "params": params, "timeout": timeout})
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: payload,
        )

    monkeypatch.setattr(weather.requests, "get", get)


def test_forecast_requests_14_days_for_configured_restaurant_location(monkeypatch):
    today = date(2030, 2, 28)
    observed = {}
    stub_open_meteo(monkeypatch, forecast_payload(today), observed)
    monkeypatch.setattr(weather.settings, "RESTAURANT_LAT", 37.32)
    monkeypatch.setattr(weather.settings, "RESTAURANT_LON", -6.84)

    result = weather.get_restaurant_weather(today=today)

    assert observed == {
        "url": "https://api.open-meteo.com/v1/forecast",
        "params": {
            "latitude": 37.32,
            "longitude": -6.84,
            "daily": ",".join(weather.DAILY_FIELDS),
            "forecast_days": 14,
            "timezone": "auto",
        },
        "timeout": 5,
    }
    assert result.count("\n") == 14
    assert "2030-02-28: máxima: 20°C; mínima: 10°C" in result
    assert "2030-03-13:" in result


def test_forecast_returns_only_an_explicit_date_in_the_horizon(monkeypatch):
    today = date(2030, 2, 28)
    observed = {}
    stub_open_meteo(monkeypatch, forecast_payload(today), observed)

    result = weather.get_restaurant_weather("2030-03-13", today=today)

    assert result.count("\n") == 1
    assert "2030-03-13: máxima: 33°C" in result


@pytest.mark.parametrize("requested_date", ["2030-02-27", "2030-03-14"])
def test_forecast_rejects_dates_outside_the_available_horizon(
    monkeypatch, requested_date
):
    today = date(2030, 2, 28)
    observed = {}
    stub_open_meteo(monkeypatch, forecast_payload(today), observed)

    result = weather.get_restaurant_weather(requested_date, today=today)

    assert requested_date in result
    assert "No hay previsión disponible" in result
    assert "máxima:" not in result


def test_forecast_rejects_incomplete_provider_data(monkeypatch):
    today = date(2030, 2, 28)
    payload = forecast_payload(today)
    payload["daily"]["wind_speed_10m_max"].pop()
    stub_open_meteo(monkeypatch, payload, {})

    assert weather.get_restaurant_weather(today=today) == weather.FORECAST_INCOMPLETE


def test_forecast_hides_provider_errors(monkeypatch):
    def fail_request(*args, **kwargs):
        raise requests.Timeout("internal provider detail")

    monkeypatch.setattr(weather.requests, "get", fail_request)

    result = weather.get_restaurant_weather(today=date(2030, 2, 28))

    assert result == weather.FORECAST_UNAVAILABLE
    assert "internal provider detail" not in result


def test_forecast_rejects_invalid_date_without_calling_provider(monkeypatch):
    def unexpected_request(*args, **kwargs):
        pytest.fail("Invalid dates must be rejected before requesting a forecast.")

    monkeypatch.setattr(weather.requests, "get", unexpected_request)

    assert "YYYY-MM-DD" in weather.get_restaurant_weather("2030-02-30")
