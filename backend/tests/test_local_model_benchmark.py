import pytest

from app.evaluation.local_model_benchmark import (
    load_evaluation_cases,
    score_grounding,
    score_retrieval,
    score_tool_call,
    summarize_retrieval,
)
from app.evaluation.embedding_migration import (
    get_vector_index_dimensions,
    vector_index_definition,
)
from app.service.menu import menu_embedding_text
from scripts import reindex_embeddings


def test_tool_call_score_checks_tool_name_and_expected_arguments():
    result = score_tool_call(
        expected_tool="search_menu",
        tool_calls=[
            {
                "function": {
                    "name": "search_menu",
                    "arguments": {
                        "query": "gazpacho",
                        "vegan_only": True,
                        "available_only": True,
                    },
                }
            }
        ],
        expected_arguments={"vegan_only": True, "available_only": True},
        required_arguments=["query"],
    )

    assert result.correct_tool
    assert result.valid_arguments


def test_tool_call_score_rejects_wrong_tools_and_unexpected_mutations():
    result = score_tool_call(
        expected_tool="get_table_reservation",
        tool_calls=[
            {
                "function": {
                    "name": "delete_table_reservation",
                    "arguments": {"reservation_id": "R-001"},
                }
            }
        ],
        expected_arguments={"reservation_id": "R-001"},
    )

    assert not result.correct_tool
    assert not result.valid_arguments


def test_tool_call_score_counts_unnecessary_calls():
    result = score_tool_call(
        expected_tool=None,
        tool_calls=[
            {"function": {"name": "search_menu", "arguments": {"query": "hola"}}}
        ],
        expected_arguments={},
    )

    assert not result.correct_tool
    assert not result.valid_arguments


def test_tool_call_score_rejects_missing_and_unexpected_arguments():
    missing = score_tool_call(
        expected_tool="search_info",
        tool_calls=[
            {"function": {"name": "search_info", "arguments": {"not_query": "terraza"}}}
        ],
        expected_arguments={},
        required_arguments=["query"],
        allowed_arguments=["query"],
    )
    unexpected = score_tool_call(
        expected_tool="search_info",
        tool_calls=[
            {
                "function": {
                    "name": "search_info",
                    "arguments": {"query": "terraza", "reservation_id": "R-001"},
                }
            }
        ],
        expected_arguments={},
        required_arguments=["query"],
        allowed_arguments=["query"],
    )

    assert not missing.valid_arguments
    assert not unexpected.valid_arguments


def test_grounding_requires_evidence_and_rejects_claims_not_in_evidence():
    grounded = score_grounding(
        "El gazpacho está disponible; contiene tomate y pepino.",
        expected_terms=["gazpacho", "tomate"],
        forbidden_terms=["sin gluten"],
    )
    unsupported = score_grounding(
        "El gazpacho está disponible y es sin gluten.",
        expected_terms=["gazpacho", "tomate"],
        forbidden_terms=["sin gluten"],
    )

    assert grounded.grounded
    assert not unsupported.grounded


def test_retrieval_reports_recall_and_reciprocal_rank_at_k():
    result = score_retrieval(
        ranked_ids=["croquetas", "gazpacho", "paella"],
        relevant_ids=["gazpacho", "paella"],
        k=3,
    )

    assert result.recall_at_k == 1.0
    assert result.reciprocal_rank == 0.5


def test_retrieval_summary_excludes_unanswerable_queries_from_mrr():
    summary = summarize_retrieval(
        [
            score_retrieval(["wrong", "right"], ["right"]),
            score_retrieval(["menu-item"], []),
        ]
    )

    assert summary.mean_reciprocal_rank == 0.5
    assert summary.recall_at_k == 1.0
    assert summary.answerable_queries == 1
    assert summary.unanswerable_queries == 1


def test_dataset_covers_spanish_grounding_retrieval_and_simulated_reservations():
    dataset = load_evaluation_cases()
    generation_cases = dataset["generation"]
    retrieval_cases = dataset["retrieval"]

    assert dataset["reference_date"] == "2026-10-05"
    assert all(case["prompt"] for case in generation_cases)
    assert any(case["expected_tool"] is None for case in generation_cases)
    assert any(case["id"].startswith("allergen-") for case in generation_cases)
    assert any(case["id"].startswith("weather-") for case in generation_cases)
    assert {
        "weather-today",
        "weather-final-horizon-day",
        "weather-past-date",
        "weather-outside-horizon",
        "weather-provider-failure",
    } <= {case["id"] for case in generation_cases}
    assert any(case.get("simulated_result") for case in generation_cases)
    assert any(not case["relevant_ids"] for case in retrieval_cases)
    assert any(case["id"].startswith("dish-") for case in retrieval_cases)


def test_vector_index_definition_uses_configured_embedding_dimensions():
    assert vector_index_definition(1024) == {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": 1024,
                "similarity": "cosine",
            }
        ]
    }


def test_vector_index_dimensions_reads_current_and_legacy_index_shapes():
    assert get_vector_index_dimensions(
        {
            "latestDefinition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": 1024,
                    }
                ]
            }
        }
    ) == 1024
    assert get_vector_index_dimensions(
        {
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": 768,
                    }
                ]
            }
        }
    ) == 768
    assert get_vector_index_dimensions({"latestDefinition": {"fields": []}}) is None


def test_menu_embedding_text_includes_the_structured_diet_and_allergen_fields():
    text = menu_embedding_text(
        {
            "name": "Gazpacho",
            "category": "entrante",
            "price": 8.5,
            "description": "Sopa fría",
            "is_vegan": True,
            "is_vegetarian": True,
            "allergens": [],
        }
    )

    assert "Plato: Gazpacho" in text
    assert "Apto para veganos: Sí" in text
    assert "Alérgenos: Ninguno" in text


@pytest.mark.asyncio
async def test_reindex_prepares_every_collection_before_modifying_indexes(monkeypatch):
    operations = []

    async def prepare(database, collection_name, embedding_model, dimensions):
        operations.append(("prepare", collection_name))
        if collection_name == "knowledge":
            raise RuntimeError("Ollama embedding request failed.")
        return ([{"_id": "menu-1"}], [[0.1] * dimensions])

    async def ensure_index(database, collection_name, dimensions):
        operations.append(("index", collection_name))

    async def store(database, collection_name, documents, vectors, dimensions):
        operations.append(("store", collection_name))
        return len(documents)

    monkeypatch.setattr(
        reindex_embeddings,
        "_prepare_collection_embeddings",
        prepare,
    )
    monkeypatch.setattr(reindex_embeddings, "_ensure_vector_index", ensure_index)
    monkeypatch.setattr(
        reindex_embeddings,
        "_store_collection_embeddings",
        store,
    )

    with pytest.raises(RuntimeError, match="embedding request failed"):
        await reindex_embeddings._migrate_collections(
            database=object(),
            collection_names=["menu", "knowledge"],
            embedding_model=object(),
            dimensions=1024,
        )

    assert operations == [("prepare", "menu"), ("prepare", "knowledge")]
