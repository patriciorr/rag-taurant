from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.rag import agent as agent_module
from main import app


def test_chat_history_is_isolated_by_session_and_continues_within_a_session(monkeypatch):
    class FakeModel:
        def __init__(self):
            self.calls = []

        async def ainvoke(self, messages):
            self.calls.append(list(messages))
            return SimpleNamespace(tool_calls=[], content="Respuesta")

    model = FakeModel()
    monkeypatch.setattr(agent_module, "llm_with_tools", model)
    monkeypatch.setattr(agent_module, "session_store", {})

    client = TestClient(app, raise_server_exceptions=False)
    first_tab_response = client.post(
        "/api/v1/chat/",
        json={"message": "Mensaje de la pestaña uno", "session_id": "tab-one"},
    )
    second_tab_response = client.post(
        "/api/v1/chat/",
        json={"message": "Mensaje de la pestaña dos", "session_id": "tab-two"},
    )
    follow_up_response = client.post(
        "/api/v1/chat/",
        json={"message": "Seguimiento de la pestaña uno", "session_id": "tab-one"},
    )

    assert first_tab_response.status_code == 200
    assert second_tab_response.status_code == 200
    assert follow_up_response.status_code == 200
    assert first_tab_response.json()["session_id"] == "tab-one"
    assert second_tab_response.json()["session_id"] == "tab-two"
    assert follow_up_response.json()["session_id"] == "tab-one"

    first_tab_history = model.calls[2][1:]
    second_tab_history = model.calls[1][1:]

    assert [(message.type, message.content) for message in first_tab_history] == [
        ("human", "Mensaje de la pestaña uno"),
        ("ai", "Respuesta"),
        ("human", "Seguimiento de la pestaña uno"),
    ]
    assert [(message.type, message.content) for message in second_tab_history] == [
        ("human", "Mensaje de la pestaña dos"),
    ]
