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
async def test_menu_search_can_list_dishes_containing_requested_allergen(monkeypatch):
    items = [
        menu_item("fish", "Arroz marinero", allergens=["pescado"]),
        menu_item("veg", "Gazpacho"),
    ]

    async def list_menu():
        return items

    async def search_similar_dishes(query, limit):
        return [{"id": item.id} for item in items]

    monkeypatch.setattr(tools_module.menu_service, "list_menu", list_menu)
    monkeypatch.setattr(tools_module.menu_service, "search_similar_dishes", search_similar_dishes)
    result = await tools_module.search_menu.ainvoke(
        {"query": "platos que sí llevan pescado", "include_allergens": ["pescado"]}
    )
    assert "Arroz marinero" in result
    assert "Gazpacho" not in result


@pytest.mark.asyncio
async def test_allergen_filter_includes_items_missing_from_vector_results(monkeypatch):
    items = [
        menu_item("first", "Arroz", allergens=["pescado"]),
        menu_item("second", "Pescado", allergens=["pescado"]),
        menu_item("other", "Gazpacho"),
    ]

    async def list_menu():
        return items

    async def search_similar_dishes(query, limit):
        return [{"id": "first"}]

    monkeypatch.setattr(tools_module.menu_service, "list_menu", list_menu)
    monkeypatch.setattr(tools_module.menu_service, "search_similar_dishes", search_similar_dishes)
    result = await tools_module.search_menu.ainvoke(
        {"query": "platos con pescado", "include_allergens": ["pescado"]}
    )
    assert "Arroz" in result and "Pescado" in result
    assert "Gazpacho" not in result


@pytest.mark.asyncio
async def test_include_exclude_allergens_and_unavailable_dishes(monkeypatch):
    items = [
        menu_item("fish", "Pescado", allergens=["pescado"]),
        menu_item("both", "Pescado con gluten", allergens=["pescado", "gluten"]),
        menu_item("closed", "Pescado agotado", allergens=["pescado"], available=False),
        menu_item("none", "Gazpacho"),
    ]

    async def list_menu():
        return items

    async def search_similar_dishes(query, limit):
        return [{"id": item.id} for item in items]

    monkeypatch.setattr(tools_module.menu_service, "list_menu", list_menu)
    monkeypatch.setattr(tools_module.menu_service, "search_similar_dishes", search_similar_dishes)
    result = await tools_module.search_menu.ainvoke(
        {
            "query": "con pescado sin gluten",
            "include_allergens": ["pescado"],
            "exclude_allergens": ["gluten"],
            "available_only": False,
        }
    )
    assert "- Pescado (" in result
    assert "Pescado agotado" in result
    assert "Pescado con gluten" not in result and "Gazpacho" not in result
    assert "no disponible" in result


@pytest.mark.asyncio
async def test_unknown_and_conflicting_allergens_are_reported(monkeypatch):
    async def list_menu():
        return [menu_item("fish", "Pescado", allergens=["pescado"])]

    monkeypatch.setattr(tools_module.menu_service, "list_menu", list_menu)
    unknown = await tools_module.search_menu.ainvoke(
        {"query": "trigo", "include_allergens": ["trigo"]}
    )
    conflict = await tools_module.search_menu.ainvoke(
        {"query": "pescado", "include_allergens": ["pescado"], "exclude_allergens": ["pescado"]}
    )
    assert "alérgenos no reconocidos" in unknown
    assert "incluir y excluir el mismo alérgeno" in conflict


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

    assert (
        result
        == "No encontré platos disponibles que coincidan con la consulta y los filtros indicados."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "tool_result"),
    [
        ("search_menu", {"query": "gazpacho"}, "Carta: Gazpacho, 8,50 €. Vegano: sí."),
        ("search_info", {"query": "horario"}, "Información recuperada: horario no disponible."),
    ],
)
async def test_chat_composes_a_response_from_retrieved_evidence(
    monkeypatch, tool_name, arguments, tool_result
):
    class FakeModel:
        calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            return SimpleNamespace(
                tool_calls=[{"name": tool_name, "args": arguments, "id": "tool-1"}],
                content="",
            )

    class Composer:
        async def ainvoke(self, messages):
            assert messages[-2].tool_calls[0]["id"] == "tool-1"
            assert messages[-1].content == tool_result
            assert messages[-1].tool_call_id == "tool-1"
            assert "exclusivamente los resultados" in messages[0].content
            return SimpleNamespace(text="El gazpacho es vegano. ¿Quieres conocer más platos?")

    class RetrievalTool:
        async def ainvoke(self, arguments):
            assert arguments == arguments_expected
            return tool_result

    model = FakeModel()
    monkeypatch.setattr(agent_module, "llm_with_tools", model)
    monkeypatch.setattr(agent_module, "llm", Composer())
    arguments_expected = arguments
    monkeypatch.setattr(agent_module, "TOOLS_MAP", {tool_name: RetrievalTool()})
    monkeypatch.setattr(agent_module, "session_store", {})
    runner = agent_module.RAGChatbotRunner()

    result = await runner.ainvoke(
        {"input": "Consulta la carta o la información del restaurante."},
        {"configurable": {"session_id": "grounded-menu"}},
    )

    assert result["output"] == "El gazpacho es vegano. ¿Quieres conocer más platos?"
    assert model.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_result",
    [
        "No se encontró información institucional sobre esa consulta.",
        "No encontré platos disponibles que coincidan con la consulta y los filtros indicados.",
        "No pude aplicar el filtro porque contiene alérgenos no reconocidos: trigo",
    ],
)
async def test_missing_evidence_is_returned_without_model_speculation(monkeypatch, tool_result):
    class Selector:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                tool_calls=[{"name": "search_info", "args": {"query": "terraza"}, "id": "1"}],
                content="",
            )

    class Tool:
        async def ainvoke(self, arguments):
            return tool_result

    class Composer:
        async def ainvoke(self, messages):
            pytest.fail("Missing evidence must not be rewritten by the model.")

    monkeypatch.setattr(agent_module, "llm_with_tools", Selector())
    monkeypatch.setattr(agent_module, "llm", Composer())
    monkeypatch.setattr(agent_module, "TOOLS_MAP", {"search_info": Tool()})
    monkeypatch.setattr(agent_module, "session_store", {})
    result = await agent_module.RAGChatbotRunner().ainvoke(
        {"input": "¿Se admiten perros en la terraza?"},
        {"configurable": {"session_id": "no-evidence"}},
    )
    assert result["output"] == tool_result


@pytest.mark.asyncio
async def test_allergy_answer_always_includes_cross_contact_notice(monkeypatch):
    class Selector:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                tool_calls=[
                    {
                        "name": "search_menu",
                        "args": {"query": "sin gluten", "exclude_allergens": ["gluten"]},
                        "id": "1",
                    }
                ],
                content="",
            )

    class Tool:
        async def ainvoke(self, arguments):
            return "Gazpacho. Alérgenos registrados: apio."

    class Composer:
        async def ainvoke(self, messages):
            return SimpleNamespace(text="El gazpacho no tiene gluten registrado.")

    monkeypatch.setattr(agent_module, "llm_with_tools", Selector())
    monkeypatch.setattr(agent_module, "llm", Composer())
    monkeypatch.setattr(agent_module, "TOOLS_MAP", {"search_menu": Tool()})
    monkeypatch.setattr(agent_module, "session_store", {})
    result = await agent_module.RAGChatbotRunner().ainvoke(
        {"input": "Tengo alergia al gluten, ¿qué puedo pedir?"},
        {"configurable": {"session_id": "allergy"}},
    )
    assert "contaminación cruzada" in result["output"]
    assert "consulta con el personal" in result["output"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "expected_notice"),
    [
        ("¿Qué platos sí llevan pescado? Soy alérgico.", True),
        ("¿Qué platos sí llevan pescado para evitarlos?", False),
        ("¿Qué platos no llevan pescado? No me gusta.", False),
    ],
)
async def test_allergy_notice_distinguishes_allergies_from_preferences(
    monkeypatch, question, expected_notice
):
    class Selector:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                tool_calls=[
                    {
                        "name": "search_menu",
                        "args": {"query": "pescado", "include_allergens": ["pescado"]},
                        "id": "1",
                    }
                ],
                content="",
            )

    class Tool:
        async def ainvoke(self, arguments):
            return "Arroz marinero: pescado registrado."

    class Composer:
        async def ainvoke(self, messages):
            return SimpleNamespace(text="El arroz marinero lleva pescado.")

    monkeypatch.setattr(agent_module, "llm_with_tools", Selector())
    monkeypatch.setattr(agent_module, "llm", Composer())
    monkeypatch.setattr(agent_module, "TOOLS_MAP", {"search_menu": Tool()})
    monkeypatch.setattr(agent_module, "session_store", {})
    result = await agent_module.RAGChatbotRunner().ainvoke(
        {"input": question}, {"configurable": {"session_id": "notice-test"}}
    )
    assert ("consulta con el personal" in result["output"]) is expected_notice


@pytest.mark.asyncio
async def test_allergy_notice_is_present_without_tool_calls(monkeypatch):
    class Model:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                tool_calls=[], content="Puedes preguntarme por los alérgenos de la carta."
            )

    monkeypatch.setattr(agent_module, "llm_with_tools", Model())
    monkeypatch.setattr(agent_module, "session_store", {})
    result = await agent_module.RAGChatbotRunner().ainvoke(
        {"input": "Tengo una alergia."},
        {"configurable": {"session_id": "no-tool-allergy"}},
    )
    assert "consulta con el personal" in result["output"]


@pytest.mark.asyncio
async def test_retrieval_failure_is_not_sent_to_the_composer(monkeypatch, caplog):
    class Selector:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                tool_calls=[{"name": "search_info", "args": {"query": "horario"}, "id": "1"}],
                content="",
            )

    class Tool:
        async def ainvoke(self, arguments):
            raise RuntimeError("database unavailable")

    class Composer:
        async def ainvoke(self, messages):
            pytest.fail("Retrieval failures must not be rewritten by the model.")

    monkeypatch.setattr(agent_module, "llm_with_tools", Selector())
    monkeypatch.setattr(agent_module, "llm", Composer())
    monkeypatch.setattr(agent_module, "TOOLS_MAP", {"search_info": Tool()})
    monkeypatch.setattr(agent_module, "session_store", {})
    result = await agent_module.RAGChatbotRunner().ainvoke(
        {"input": "¿Cuál es el horario?"},
        {"configurable": {"session_id": "retrieval-failure"}},
    )
    assert "No pude consultar" in result["output"]
    assert "database unavailable" in caplog.text


@pytest.mark.asyncio
async def test_composition_failure_is_logged_and_reported(monkeypatch, caplog):
    class Selector:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                tool_calls=[{"name": "search_info", "args": {"query": "horario"}, "id": "1"}],
                content="",
            )

    class Tool:
        async def ainvoke(self, arguments):
            return "Abierto de 12:00 a 23:00."

    class Composer:
        async def ainvoke(self, messages):
            raise RuntimeError("model unavailable")

    monkeypatch.setattr(agent_module, "llm_with_tools", Selector())
    monkeypatch.setattr(agent_module, "llm", Composer())
    monkeypatch.setattr(agent_module, "TOOLS_MAP", {"search_info": Tool()})
    monkeypatch.setattr(agent_module, "session_store", {})
    result = await agent_module.RAGChatbotRunner().ainvoke(
        {"input": "¿Cuál es el horario?"},
        {"configurable": {"session_id": "composition-failure"}},
    )
    assert "No pude preparar una respuesta" in result["output"]
    assert "model unavailable" in caplog.text


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


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["", "  ", None])
async def test_empty_model_search_query_uses_customer_request(monkeypatch, query):
    received = {}

    class MenuTool:
        async def ainvoke(self, arguments):
            received.update(arguments)
            return "ok"

    monkeypatch.setattr(agent_module, "TOOLS_MAP", {"search_menu": MenuTool()})
    runner = agent_module.RAGChatbotRunner()
    await runner._invoke_tool(
        "search_menu",
        {"query": query, "vegan_only": True},
        "s1",
        user_text="  Recomiéndame opciones veganas  ",
    )
    assert received == {"query": "Recomiéndame opciones veganas", "vegan_only": True}
