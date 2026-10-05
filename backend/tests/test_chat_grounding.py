from types import SimpleNamespace

import pytest

from app.models.menu import MenuItem
from app.rag import agent as agent_module
from app.rag import tools as tools_module


def menu_item(
    item_id,
    name,
    *,
    allergens=(),
    is_vegan=False,
    is_vegetarian=False,
    available=True,
):
    return MenuItem(
        id=item_id,
        name=name,
        description=f"Descripción de {name}.",
        price=10,
        category="principal",
        allergens=list(allergens),
        is_vegan=is_vegan,
        is_vegetarian=is_vegetarian,
        available=available,
    )


@pytest.mark.asyncio
async def test_menu_search_applies_diet_allergen_and_availability_filters(monkeypatch):
    items = [
        menu_item(
            "burger",
            "Hamburguesa vegana",
            allergens=["gluten"],
            is_vegan=True,
            is_vegetarian=True,
        ),
        menu_item("gazpacho", "Gazpacho", is_vegan=True, is_vegetarian=True),
        menu_item(
            "dessert",
            "Postre vegano",
            is_vegan=True,
            is_vegetarian=True,
            available=False,
        ),
    ]
    observed = {}

    async def list_menu():
        return items

    async def search_similar_dishes(query, limit):
        observed["query"] = query
        observed["limit"] = limit
        return [{"id": item.id} for item in items]

    monkeypatch.setattr(tools_module.menu_service, "list_menu", list_menu)
    monkeypatch.setattr(tools_module.menu_service, "search_similar_dishes", search_similar_dishes)

    result = await tools_module.search_menu.ainvoke(
        {
            "query": "opciones veganas",
            "vegan_only": True,
            "vegetarian_only": True,
            "exclude_allergens": ["gluten"],
        }
    )

    assert observed == {"query": "opciones veganas", "limit": 3}
    assert "Gazpacho" in result
    assert "Hamburguesa vegana" not in result
    assert "Postre vegano" not in result
    assert "ninguno registrado" in result
    assert "no se puede garantizar" in result


@pytest.mark.asyncio
async def test_menu_search_reports_when_filters_leave_no_evidence(monkeypatch):
    async def list_menu():
        return [menu_item("dish", "Plato con gluten", allergens=["gluten"])]

    async def search_similar_dishes(query, limit):
        return [{"id": "dish"}]

    monkeypatch.setattr(tools_module.menu_service, "list_menu", list_menu)
    monkeypatch.setattr(tools_module.menu_service, "search_similar_dishes", search_similar_dishes)

    result = await tools_module.search_menu.ainvoke(
        {"query": "plato sin gluten", "exclude_allergens": ["gluten"]}
    )

    assert result == "No encontré platos disponibles que coincidan con la consulta y los filtros indicados."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "tool_result"),
    [
        ("search_menu", {"query": "gazpacho"}, "Carta: Gazpacho, 8,50 €. Vegano: sí."),
        ("search_info", {"query": "horario"}, "Información recuperada: horario no disponible."),
    ],
)
async def test_chat_returns_retrieved_evidence_without_model_rewriting_it(
    monkeypatch, tool_name, arguments, tool_result
):
    class FakeModel:
        calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            return SimpleNamespace(
                tool_calls=[{"name": tool_name, "args": arguments}],
                content="",
            )

    class RetrievalTool:
        async def ainvoke(self, arguments):
            assert arguments == arguments_expected
            return tool_result

    model = FakeModel()
    monkeypatch.setattr(agent_module, "llm_with_tools", model)
    arguments_expected = arguments
    monkeypatch.setattr(agent_module, "TOOLS_MAP", {tool_name: RetrievalTool()})
    monkeypatch.setattr(agent_module, "session_store", {})
    runner = agent_module.RAGChatbotRunner()

    result = await runner.ainvoke(
        {"input": "Consulta la carta o la información del restaurante."},
        {"configurable": {"session_id": "grounded-menu"}},
    )

    assert result["output"] == tool_result
    assert model.calls == 1


@pytest.mark.asyncio
async def test_chat_prompt_limits_scope_and_refuses_unrelated_requests(monkeypatch):
    refusal = "Lo siento, solo puedo ayudar con información y servicios de RAGtaurant."

    class FakeModel:
        async def ainvoke(self, messages):
            assert "Declina brevemente cualquier petición ajena" in messages[0].content
            return SimpleNamespace(tool_calls=[], content=refusal)

    monkeypatch.setattr(agent_module, "llm_with_tools", FakeModel())
    monkeypatch.setattr(agent_module, "session_store", {})
    runner = agent_module.RAGChatbotRunner()

    result = await runner.ainvoke(
        {"input": "Explícame cómo resolver una ecuación diferencial."},
        {"configurable": {"session_id": "out-of-scope"}},
    )

    assert result["output"] == refusal


@pytest.mark.asyncio
async def test_search_menu_arguments_from_model_are_normalized(monkeypatch):
    received = {}

    class MenuTool:
        async def ainvoke(self, arguments):
            received.update(arguments)
            return "ok"

    monkeypatch.setattr(agent_module, "TOOLS_MAP", {"search_menu": MenuTool()})
    runner = agent_module.RAGChatbotRunner()

    await runner._invoke_tool(
        "search_menu",
        {
            "query": "gluten",
            "vegan_only": None,
            "exclude_allergens": "Gluten, lácteos",
            "available_only": "true",
        },
        "s1",
    )

    assert received == {
        "query": "gluten",
        "exclude_allergens": ["gluten", "lácteos"],
        "available_only": True,
    }
