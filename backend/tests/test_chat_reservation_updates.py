from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.models import reservation as reservation_models
from app.models.reservation import ReservationInDB
from app.rag import agent as agent_module
from app.core.exceptions import ReservationNotFoundException


@pytest.fixture(autouse=True)
def reservation_clock(monkeypatch):
    now = datetime(2030, 2, 27, 10, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)


def reservation(**overrides):
    values = {
        "reservation_id": "RES-1",
        "customer_name": "Ana Perez",
        "email": "ana@example.com",
        "phone": "+34612345678",
        "date": "2030-02-28",
        "time": "18:30",
        "guests": 2,
        "created_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
        "status": "confirmed",
    }
    return ReservationInDB(**{**values, **overrides})


class FakeModel:
    def __init__(self, tool_call):
        self.tool_call = tool_call

    async def ainvoke(self, messages):
        return SimpleNamespace(tool_calls=[self.tool_call], content="")


@pytest.mark.asyncio
async def test_reservation_edit_is_authorized_summarized_and_applied_only_after_confirmation(monkeypatch):
    tool_call = {
        "name": "edit_table_reservation",
        "args": {
            "reservation_id": "RES-1",
            "email": "ANA@example.com",
            "phone": "612 345 678",
            "date": "2030-03-01",
            "time": "19:00",
            "guests": 4,
        },
        "id": "edit-1",
    }
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(agent_module, "llm_with_tools", FakeModel(tool_call))
    fetched = []
    updates = []

    async def get_reservation(reservation_id, contact):
        fetched.append((reservation_id, contact.email, contact.phone))
        return reservation()

    async def update_reservation(reservation_id, update, contact):
        updates.append((reservation_id, update.model_dump(exclude_unset=True), contact.email, contact.phone))
        return reservation(date=update.date, time=update.time, guests=update.guests)

    monkeypatch.setattr(agent_module.reservation_service, "get_reservation", get_reservation)
    monkeypatch.setattr(agent_module.reservation_service, "update_reservation", update_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": "edit-tab"}}

    proposed = await runner.ainvoke({"input": "Cambia mi reserva"}, config)

    assert fetched == [("RES-1", "ana@example.com", "+34612345678")]
    assert "2030-03-01" in proposed["output"]
    assert "19:00" in proposed["output"]
    assert "4" in proposed["output"]
    assert "todavía no se ha modificado" in proposed["output"].lower()
    assert updates == []

    completed = await runner.ainvoke({"input": "Sí, confirmar"}, config)

    assert "se ha modificado" in completed["output"].lower()
    assert updates == [
        ("RES-1", {"date": "2030-03-01", "time": "19:00", "guests": 4}, "ana@example.com", "+34612345678")
    ]


@pytest.mark.asyncio
async def test_reservation_read_returns_only_authorized_reservation_details(monkeypatch):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(
            {
                "name": "get_table_reservation",
                "args": {
                    "reservation_id": "RES-1",
                    "email": "ANA@example.com",
                    "phone": "612 345 678",
                },
                "id": "read-1",
            }
        ),
    )

    async def get_reservation(reservation_id, contact):
        assert reservation_id == "RES-1"
        assert (contact.email, contact.phone) == ("ana@example.com", "+34612345678")
        return reservation()

    monkeypatch.setattr(agent_module.reservation_service, "get_reservation", get_reservation)
    runner = agent_module.RAGChatbotRunner()
    result = await runner.ainvoke(
        {"input": "Consulta RES-1"},
        {"configurable": {"session_id": "read-tab"}},
    )

    assert "reserva verificada (activa)" in result["output"].lower()
    assert "2030-02-28" in result["output"]
    assert "18:30" in result["output"]
    assert "2" in result["output"]
    assert "ana@example.com" not in result["output"]
    assert "+34612345678" not in result["output"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        {"reservation_id": "RES-1", "email": "wrong@example.com", "phone": "+34612345678"},
        {"reservation_id": "RES-1", "email": "ana@example.com", "phone": "+34600000000"},
        {"reservation_id": "RES-1", "phone": "+34612345678"},
    ],
)
async def test_reservation_read_does_not_reveal_details_without_matching_contacts(
    monkeypatch, arguments
):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(
            {
                "name": "get_table_reservation",
                "args": arguments,
                "id": "read-unauthorized",
            }
        ),
    )

    async def get_reservation(*args):
        raise ReservationNotFoundException("RES-1")

    monkeypatch.setattr(agent_module.reservation_service, "get_reservation", get_reservation)
    result = await agent_module.RAGChatbotRunner().ainvoke(
        {"input": "Consulta la reserva"},
        {"configurable": {"session_id": "unauthorized-read"}},
    )

    assert "no se encontró una reserva autorizada" in result["output"].lower()
    assert "Ana Perez" not in result["output"]
    assert "2030-02-28" not in result["output"]
    assert "18:30" not in result["output"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        {
            "reservation_id": "RES-1",
            "email": "ana@example.com",
            "phone": "+34600000000",
            "guests": 4,
        },
        {
            "reservation_id": "RES-1",
            "phone": "+34612345678",
            "guests": 4,
        },
    ],
)
async def test_reservation_edit_does_not_propose_changes_without_matching_contacts(
    monkeypatch, arguments
):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(
            {
                "name": "edit_table_reservation",
                "args": arguments,
                "id": "edit-unauthorized",
            }
        ),
    )

    async def get_reservation(*args):
        raise ReservationNotFoundException("RES-1")

    monkeypatch.setattr(agent_module.reservation_service, "get_reservation", get_reservation)
    runner = agent_module.RAGChatbotRunner()
    result = await runner.ainvoke(
        {"input": "Cambia la reserva"},
        {"configurable": {"session_id": "unauthorized-edit"}},
    )

    assert "no se encontró una reserva autorizada" in result["output"].lower()
    assert "2030-02-28" not in result["output"]
    assert "18:30" not in result["output"]
    assert runner.pending_updates == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "still_pending"),
    [("No, gracias", False), ("Quizá luego", True)],
)
async def test_reservation_edit_waits_for_an_affirmative_confirmation(
    monkeypatch, answer, still_pending
):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(
            {
                "name": "edit_table_reservation",
                "args": {
                    "reservation_id": "RES-1",
                    "email": "ana@example.com",
                    "phone": "+34612345678",
                    "guests": 4,
                },
                "id": "edit-confirmation",
            }
        ),
    )
    updates = []

    async def get_reservation(reservation_id, contact):
        return reservation()

    async def update_reservation(*args):
        updates.append(args)
        return reservation(guests=4)

    monkeypatch.setattr(agent_module.reservation_service, "get_reservation", get_reservation)
    monkeypatch.setattr(agent_module.reservation_service, "update_reservation", update_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": f"edit-{answer}"}}

    await runner.ainvoke({"input": "Cambia los comensales"}, config)
    result = await runner.ainvoke({"input": answer}, config)

    assert updates == []
    assert ("edit-" + answer in runner.pending_updates) is still_pending
    if still_pending:
        assert "sigue pendiente" in result["output"].lower()
    else:
        assert "no se ha modificado" in result["output"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [("date", "2030-03-14"), ("time", "11:30")],
)
async def test_reservation_edit_reuses_reservation_schedule_validation(
    monkeypatch, field, value
):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(
            {
                "name": "edit_table_reservation",
                "args": {
                    "reservation_id": "RES-1",
                    "email": "ana@example.com",
                    "phone": "+34612345678",
                    field: value,
                },
                "id": "edit-invalid-schedule",
            }
        ),
    )

    async def get_reservation(reservation_id, contact):
        return reservation()

    monkeypatch.setattr(agent_module.reservation_service, "get_reservation", get_reservation)
    runner = agent_module.RAGChatbotRunner()
    result = await runner.ainvoke(
        {"input": "Cambia la reserva"},
        {"configurable": {"session_id": "invalid-schedule"}},
    )

    assert "no se ha modificado la reserva" in result["output"].lower()
    assert runner.pending_updates == {}


@pytest.mark.asyncio
async def test_reservation_edit_rejects_fields_outside_the_editable_set(monkeypatch):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(
            {
                "name": "edit_table_reservation",
                "args": {
                    "reservation_id": "RES-1",
                    "email": "ana@example.com",
                    "phone": "+34612345678",
                    "customer_name": "Someone Else",
                },
                "id": "edit-name",
            }
        ),
    )

    async def get_reservation(*args):
        pytest.fail("Unsupported edits must be rejected before reading a reservation.")

    async def update_reservation(*args):
        pytest.fail("Unsupported fields must never modify a reservation.")

    monkeypatch.setattr(agent_module.reservation_service, "get_reservation", get_reservation)
    monkeypatch.setattr(agent_module.reservation_service, "update_reservation", update_reservation)
    runner = agent_module.RAGChatbotRunner()
    result = await runner.ainvoke(
        {"input": "Cambia el nombre"},
        {"configurable": {"session_id": "edit-name"}},
    )

    assert "no se encontró una reserva autorizada" in result["output"].lower()
    assert runner.pending_updates == {}
