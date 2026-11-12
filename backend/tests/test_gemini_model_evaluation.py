from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from scripts import evaluate_gemini_models as evaluation


@pytest.mark.asyncio
async def test_candidate_embeddings_use_text_instructions_without_task_type():
    embed_content = AsyncMock(
        return_value=SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1] * evaluation.DIMENSIONS)]
        )
    )
    service = SimpleNamespace(
        client=SimpleNamespace(
            aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content))
        )
    )
    text = evaluation.query_text("¿Qué vino?")

    vectors = await evaluation.embed_texts(service, [text])

    request = embed_content.await_args.kwargs
    assert request["model"] == "gemini-embedding-2"
    assert request["config"].task_type is None
    assert request["config"].output_dimensionality == 1536
    assert request["contents"] == [
        {"parts": [{"text": "task: question answering | query: ¿Qué vino?"}]}
    ]
    assert len(vectors[0]) == 1536


def test_candidate_document_format_and_cosine():
    assert evaluation.document_text({"name": "Agua", "description": "Natural"}).startswith(
        "title: Agua | text: Plato: Agua"
    )
    assert evaluation.cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    with pytest.raises(ValueError, match="different dimensions"):
        evaluation.cosine([1.0], [1.0, 2.0])
    with pytest.raises(ValueError, match="zero-length"):
        evaluation.cosine([0.0], [1.0])


@pytest.mark.asyncio
async def test_candidate_embeddings_reject_invalid_response():
    service = SimpleNamespace(
        client=SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(
                    embed_content=AsyncMock(return_value=SimpleNamespace(embeddings=[]))
                )
            )
        )
    )
    with pytest.raises(ValueError, match="unexpected count or dimension"):
        await evaluation.embed_texts(service, ["text"])


@pytest.mark.asyncio
async def test_evaluator_runs_tool_round_trip_without_other_models(monkeypatch):
    models = []

    def embeddings_factory(**kwargs):
        models.append(kwargs["model"])
        return object()

    class FakeChat:
        def __init__(self, **kwargs):
            models.append(kwargs["model"])
            assert kwargs["thinking_level"] == "medium"
            self.invoke = AsyncMock(
                side_effect=[
                    AIMessage(
                        content="",
                        tool_calls=[
                            {"name": "search_menu", "args": {"query": "gazpacho"}, "id": "call-1"}
                        ],
                    ),
                    AIMessage(content="Gazpacho: 8,50 euros."),
                ]
            )

        def bind_tools(self, tools):
            return SimpleNamespace(ainvoke=self.invoke)

    async def embed_texts(service, texts):
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(evaluation.settings, "GOOGLE_API_KEY", "fake-test-key")
    monkeypatch.setattr(evaluation, "GoogleGenerativeAIEmbeddings", embeddings_factory)
    monkeypatch.setattr(evaluation, "ChatGoogleGenerativeAI", FakeChat)
    monkeypatch.setattr(evaluation, "embed_texts", embed_texts)
    monkeypatch.setattr(evaluation, "CASES", (evaluation.CASES[0],))

    result = await evaluation.evaluate()

    assert models == ["gemini-embedding-2", "gemini-3.8-flash"]
    assert result["results"][0]["used_search_tool"]
    assert result["results"][0]["answer"] == "Gazpacho: 8,50 euros."
