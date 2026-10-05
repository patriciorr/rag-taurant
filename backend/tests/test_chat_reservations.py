from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.core.exceptions import DatabaseException, ReservationConflictException
from app.models import reservation as reservation_models
from app.models.reservation import ReservationCreate
from app.rag import agent as agent_module
from app.rag import tools as tools_module


@pytest.fixture(autouse=True)
def reservation_clock(monkeypatch):
    now = datetime(2030, 2, 27, 10, 15, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)


def create_call(arguments):
    return {
        "name": "make_table_reservation",
        "args": arguments,
        "id": "create-1",
    }


def valid_arguments():
    return {
        "customer_name": "Ana Perez",
        "email": "ANA@example.com",
        "phone": "612 345 678",
        "date": "2030-02-28",
        "time": "18:30",
        "guests": 2,
    }


class FakeModel:
    def __init__(self, *responses):
        self.responses = iter(responses)

    async def ainvoke(self, messages):
        return next(self.responses)


def tool_response(arguments):
    return SimpleNamespace(tool_calls=[create_call(arguments)], content="")


def text_response(content="Respuesta"):
    return SimpleNamespace(tool_calls=[], content=content)


@pytest.mark.asyncio
async def test_create_proposes_normalized_summary_and_persists_only_after_confirmation(monkeypatch):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(tool_response(valid_arguments())),
    )
    persisted = []

    async def create_reservation(reservation):
        assert isinstance(reservation, ReservationCreate)
        persisted.append(reservation)
        return SimpleNamespace(reservation_id="RES-1234")

    monkeypatch.setattr(agent_module.reservation_service, "create_reservation", create_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": "create-tab"}}

    proposed = await runner.ainvoke({"input": "Quiero reservar"}, config)

    assert "ANA@example.com" not in proposed["output"]
    assert "ana@example.com" in proposed["output"]
    assert "+34612345678" in proposed["output"]
    assert "2030-02-28" in proposed["output"]
    assert "18:30" in proposed["output"]
    assert "- Comensales: 2" in proposed["output"]
    assert "Todavía no se ha creado" in proposed["output"]
    assert persisted == []

    completed = await runner.ainvoke({"input": "Sí, confirmar"}, config)

    assert "RES-1234" in completed["output"]
    assert len(persisted) == 1
    assert persisted[0].model_dump(mode="json") == {
        "customer_name": "Ana Perez",
        "email": "ana@example.com",
        "phone": "+34612345678",
        "date": "2030-02-28",
        "time": "18:30",
        "guests": 2,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("No, gracias", "no se ha creado la reserva"),
        ("Quizá más tarde", "la solicitud sigue pendiente"),
    ],
)
async def test_decline_or_ambiguous_reply_never_creates(answer, expected, monkeypatch):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(tool_response(valid_arguments())),
    )

    async def create_reservation(*args):
        pytest.fail("A non-affirmative response must not create a reservation.")

    monkeypatch.setattr(agent_module.reservation_service, "create_reservation", create_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": f"decline-{answer}"}}

    await runner.ainvoke({"input": "Prepara una reserva"}, config)
    result = await runner.ainvoke({"input": answer}, config)

    assert expected in result["output"].lower()


@pytest.mark.asyncio
async def test_pending_creation_is_bound_to_its_session(monkeypatch):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(tool_response(valid_arguments()), text_response()),
    )
    created = []

    async def create_reservation(reservation):
        created.append(reservation)
        return SimpleNamespace(reservation_id="RES-1234")

    monkeypatch.setattr(agent_module.reservation_service, "create_reservation", create_reservation)
    runner = agent_module.RAGChatbotRunner()

    await runner.ainvoke(
        {"input": "Prepara una reserva"},
        {"configurable": {"session_id": "tab-one"}},
    )
    other_session = await runner.ainvoke(
        {"input": "Sí"},
        {"configurable": {"session_id": "tab-two"}},
    )

    assert other_session["output"] == "Respuesta"
    assert created == []

    completed = await runner.ainvoke(
        {"input": "Sí"},
        {"configurable": {"session_id": "tab-one"}},
    )

    assert "RES-1234" in completed["output"]
    assert len(created) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "expected_message"),
    [
        (
            {key: value for key, value in valid_arguments().items() if key != "email"},
            "falta el email",
        ),
        (
            {**valid_arguments(), "date": "2030-03-14"},
            "entre hoy y los próximos 13 días",
        ),
    ],
)
async def test_invalid_creation_data_is_explained_without_pending_confirmation(
    arguments, expected_message, monkeypatch
):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(tool_response(arguments)),
    )
    now = datetime(2030, 2, 28, 10, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    monkeypatch.setattr(reservation_models, "restaurant_now", lambda: now)
    runner = agent_module.RAGChatbotRunner()

    result = await runner.ainvoke(
        {"input": "Prepara una reserva"},
        {"configurable": {"session_id": "invalid-create"}},
    )

    assert expected_message in result["output"].lower()
    assert "no he creado ninguna reserva" in result["output"].lower()
    assert runner.pending_creations == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "expected_message"),
    [
        (
            ReservationConflictException(),
            "ya existe una reserva activa",
        ),
        (
            DatabaseException("database details"),
            "no se pudo registrar la reserva",
        ),
    ],
)
async def test_service_failures_never_report_a_created_reservation(
    failure, expected_message, monkeypatch, caplog
):
    monkeypatch.setattr(agent_module, "session_store", {})
    monkeypatch.setattr(
        agent_module,
        "llm_with_tools",
        FakeModel(tool_response(valid_arguments())),
    )

    async def create_reservation(reservation):
        raise failure

    monkeypatch.setattr(agent_module.reservation_service, "create_reservation", create_reservation)
    runner = agent_module.RAGChatbotRunner()
    config = {"configurable": {"session_id": "failed-create"}}
    await runner.ainvoke({"input": "Prepara una reserva"}, config)

    result = await runner.ainvoke({"input": "Sí"}, config)

    assert expected_message in result["output"].lower()
    assert "se ha creado correctamente" not in result["output"].lower()
    if isinstance(failure, DatabaseException):
        assert "Failed to create a confirmed reservation" in caplog.text


@pytest.mark.asyncio
async def test_creation_tool_only_prepares_a_validated_summary(monkeypatch):
    async def create_reservation(*args):
        pytest.fail("The preparation tool must not persist a reservation.")

    monkeypatch.setattr(tools_module.reservation_service, "create_reservation", create_reservation)

    result = await tools_module.make_table_reservation.ainvoke(valid_arguments())

    assert "Todavía no se ha creado" in result
    assert "ana@example.com" in result
