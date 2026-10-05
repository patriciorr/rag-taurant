from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.reservation import ReservationInDB
from app.rag import agent as agent_module


def reservation(status: str) -> ReservationInDB:
    return ReservationInDB(
        reservation_id="RES-1",
        customer_name="Ana Perez",
        email="ana@example.com",
        phone="+34612345678",
        date="2030-02-28",
        time="18:30",
        guests=2,
        created_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        status=status,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_date"),
    [("confirmed", "2030-02-28"), ("cancelled", None)],
)
async def test_weather_uses_only_a_verified_active_reservation_date(
    monkeypatch, status, expected_date
):
    class FakeModel:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    tool_calls=[
                        {
                            "name": "get_table_reservation",
                            "args": {
                                "reservation_id": "RES-1",
                                "email": "ana@example.com",
                                "phone": "+34612345678",
                            },
                            "id": "reservation-1",
                        }
                    ],
                    content="",
                )
            if self.calls == 2:
                return SimpleNamespace(tool_calls=[], content="Reserva consultada.")
            return SimpleNamespace(
                tool_calls=[
                    {
                        "name": "get_weather_forecast",
                        "args": {"date": None},
                        "id": "weather-1",
                    }
                ],
                content="",
            )

    class WeatherTool:
        def __init__(self):
            self.arguments = None

        async def ainvoke(self, arguments):
            self.arguments = arguments
            return "Previsión consultada."

    async def get_verified_table_reservation(**arguments):
        assert arguments == {
            "reservation_id": "RES-1",
            "email": "ana@example.com",
            "phone": "+34612345678",
        }
        return reservation(status)

    weather_tool = WeatherTool()
    monkeypatch.setattr(agent_module, "llm_with_tools", FakeModel())
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "get_verified_table_reservation",
        get_verified_table_reservation,
    )
    monkeypatch.setitem(agent_module.TOOLS_MAP, "get_weather_forecast", weather_tool)

    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": "weather-context"}}

    await runner.ainvoke({"input": "Consulta mi reserva."}, config)
    result = await runner.ainvoke(
        {"input": "¿Qué tiempo hará el día de mi reserva?"},
        config,
    )

    assert result["output"] == "Previsión consultada."
    assert weather_tool.arguments == (
        {"date": expected_date} if expected_date else {"date": None}
    )


@pytest.mark.asyncio
async def test_verified_reservation_weather_context_is_session_scoped(monkeypatch):
    class WeatherTool:
        def __init__(self):
            self.arguments = None

        async def ainvoke(self, arguments):
            self.arguments = arguments
            return "Previsión consultada."

    weather_tool = WeatherTool()
    monkeypatch.setitem(agent_module.TOOLS_MAP, "get_weather_forecast", weather_tool)
    runner = agent_module.RAGChatbotRunner()
    runner.verified_reservations["tab-one"] = ("RES-1", "2030-02-28")

    await runner._invoke_tool(
        "get_weather_forecast",
        {"date": None},
        "tab-two",
    )

    assert weather_tool.arguments == {"date": None}
