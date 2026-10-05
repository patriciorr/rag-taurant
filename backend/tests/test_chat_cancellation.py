from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.exceptions import DatabaseException
from app.models.reservation import ReservationInDB
from app.rag import agent as agent_module
from app.rag import tools as tools_module


def reservation():
    return ReservationInDB(
        reservation_id="RES-1",
        customer_name="Ana Perez",
        email="ana@example.com",
        phone="+34612345678",
        date="2030-02-28",
        time="18:30",
        guests=2,
        created_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        status="confirmed",
    )


@pytest.mark.asyncio
async def test_cancel_tool_verifies_all_contact_details_without_cancelling(monkeypatch):
    fetched = {}

    async def get_reservation(reservation_id, contact):
        fetched["reservation_id"] = reservation_id
        fetched["email"] = contact.email
        fetched["phone"] = contact.phone
        return reservation()

    async def cancel_reservation(*args):
        pytest.fail("The tool must wait for an explicit confirmation.")

    monkeypatch.setattr(tools_module.reservation_service, "get_reservation", get_reservation)
    monkeypatch.setattr(tools_module.reservation_service, "cancel_reservation", cancel_reservation)

    result = await tools_module.delete_table_reservation.ainvoke(
        {
            "reservation_id": "RES-1",
            "email": "ANA@example.com",
            "phone": "612 345 678",
        }
    )

    assert fetched == {
        "reservation_id": "RES-1",
        "email": "ana@example.com",
        "phone": "+34612345678",
    }
    assert "18:30" in result
    assert "confirm" in result.lower()


@pytest.mark.asyncio
async def test_chatbot_cancels_only_after_explicit_confirmation(monkeypatch):
    class FakeModel:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    tool_calls=[
                        {
                            "name": "delete_table_reservation",
                            "args": {
                                "reservation_id": "RES-1",
                                "email": "ana@example.com",
                                "phone": "+34612345678",
                            },
                            "id": "cancel-1",
                        }
                    ],
                    content="",
                )
            return SimpleNamespace(tool_calls=[], content="¿Confirma la cancelación de RES-1?")

    class CancellationTool:
        async def ainvoke(self, arguments):
            return "Reserva RES-1, 28/02/2030 a las 18:30. ¿Confirma la cancelación?"

    cancellations = []

    async def cancel_reservation(reservation_id, contact):
        cancellations.append((reservation_id, contact.email, contact.phone))

    monkeypatch.setattr(agent_module, "llm_with_tools", FakeModel())
    monkeypatch.setitem(agent_module.TOOLS_MAP, "delete_table_reservation", CancellationTool())
    monkeypatch.setattr(agent_module.reservation_service, "cancel_reservation", cancel_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": "confirmed-cancel-test"}}

    proposed = await runner.ainvoke({"input": "Quiero cancelar RES-1"}, config)
    assert "confirma" in proposed["output"].lower()
    assert cancellations == []

    completed = await runner.ainvoke({"input": "Sí, confirmar"}, config)

    assert "cancelada" in completed["output"].lower()
    assert cancellations == [("RES-1", "ana@example.com", "+34612345678")]


@pytest.mark.asyncio
async def test_chatbot_keeps_cancellation_pending_after_a_database_failure(monkeypatch):
    class FakeModel:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                tool_calls=[
                    {
                        "name": "delete_table_reservation",
                        "args": {
                            "reservation_id": "RES-1",
                            "email": "ana@example.com",
                            "phone": "+34612345678",
                        },
                        "id": "cancel-retry",
                    }
                ],
                content="",
            )

    class CancellationTool:
        async def ainvoke(self, arguments):
            return "¿Confirma la cancelación de RES-1?"

    attempts = 0

    async def cancel_reservation(reservation_id, contact):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise DatabaseException("database unavailable")

    monkeypatch.setattr(agent_module, "llm_with_tools", FakeModel())
    monkeypatch.setitem(agent_module.TOOLS_MAP, "delete_table_reservation", CancellationTool())
    monkeypatch.setattr(agent_module.reservation_service, "cancel_reservation", cancel_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": "retry-cancellation"}}

    await runner.ainvoke({"input": "Quiero cancelar RES-1"}, config)
    failed = await runner.ainvoke({"input": "Sí, confirmar"}, config)

    assert "no se pudo completar la cancelación" in failed["output"].lower()
    assert "retry-cancellation" in runner.pending_cancellations
    assert attempts == 1

    retried = await runner.ainvoke({"input": "Sí, confirmar"}, config)

    assert "cancelada" in retried["output"].lower()
    assert "retry-cancellation" not in runner.pending_cancellations
    assert attempts == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["No, gracias", "¿Qué tiempo hará mañana?"])
async def test_chatbot_does_not_cancel_without_an_explicit_yes(monkeypatch, answer):
    class FakeModel:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    tool_calls=[
                        {
                            "name": "delete_table_reservation",
                            "args": {
                                "reservation_id": "RES-1",
                                "email": "ana@example.com",
                                "phone": "+34612345678",
                            },
                            "id": "cancel-1",
                        }
                    ],
                    content="",
                )
            return SimpleNamespace(tool_calls=[], content="¿Confirma la cancelación de RES-1?")

    class CancellationTool:
        async def ainvoke(self, arguments):
            return "¿Confirma la cancelación de RES-1?"

    async def cancel_reservation(*args):
        pytest.fail("A cancellation must not happen without an explicit yes.")

    monkeypatch.setattr(agent_module, "llm_with_tools", FakeModel())
    monkeypatch.setitem(agent_module.TOOLS_MAP, "delete_table_reservation", CancellationTool())
    monkeypatch.setattr(agent_module.reservation_service, "cancel_reservation", cancel_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": f"declined-cancel-{answer}"}}

    await runner.ainvoke({"input": "Quiero cancelar RES-1"}, config)
    response = await runner.ainvoke({"input": answer}, config)

    assert cancellations_not_called_message(answer, response["output"])


def cancellations_not_called_message(answer, response):
    if answer.startswith("No"):
        return "no se ha cancelado" in response.lower()
    return "cancelación sigue pendiente" in response.lower()
