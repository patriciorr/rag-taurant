import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "evaluation"
    / "local_model_evaluation.json"
)


@dataclass(frozen=True)
class ToolCallScore:
    correct_tool: bool
    valid_arguments: bool


@dataclass(frozen=True)
class GroundingScore:
    required_terms_present: bool
    forbidden_terms_absent: bool

    @property
    def grounded(self) -> bool:
        return self.required_terms_present and self.forbidden_terms_absent


@dataclass(frozen=True)
class RetrievalScore:
    recall_at_k: float | None
    reciprocal_rank: float


@dataclass(frozen=True)
class RetrievalSummary:
    recall_at_k: float
    mean_reciprocal_rank: float
    answerable_queries: int
    unanswerable_queries: int


def _normalized(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def load_evaluation_cases() -> dict[str, Any]:
    with DATASET_PATH.open(encoding="utf-8") as dataset_file:
        dataset = json.load(dataset_file)
    if not isinstance(dataset, dict) or not {"generation", "retrieval"} <= dataset.keys():
        raise ValueError(f"Invalid local-model evaluation dataset: {DATASET_PATH}")
    return dataset


def score_tool_call(
    expected_tool: str | None,
    tool_calls: Sequence[Mapping[str, Any]],
    expected_arguments: Mapping[str, Any],
    required_arguments: Sequence[str] = (),
    allowed_arguments: Sequence[str] | None = None,
) -> ToolCallScore:
    if expected_tool is None:
        abstained = not tool_calls
        return ToolCallScore(correct_tool=abstained, valid_arguments=abstained)
    if len(tool_calls) != 1:
        return ToolCallScore(correct_tool=False, valid_arguments=False)

    function = tool_calls[0].get("function")
    if not isinstance(function, Mapping) or function.get("name") != expected_tool:
        return ToolCallScore(correct_tool=False, valid_arguments=False)

    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = None
    if not isinstance(arguments, Mapping):
        return ToolCallScore(correct_tool=True, valid_arguments=False)

    valid_arguments = (
        all(key in arguments for key in required_arguments)
        and (
            allowed_arguments is None
            or set(arguments) <= set(allowed_arguments)
        )
        and all(
        key in arguments
        and type(arguments[key]) is type(value)
        and arguments[key] == value
        for key, value in expected_arguments.items()
        )
    )
    return ToolCallScore(correct_tool=True, valid_arguments=valid_arguments)


def score_grounding(
    response: str,
    expected_terms: Sequence[str],
    forbidden_terms: Sequence[str],
) -> GroundingScore:
    normalized_response = _normalized(response)
    return GroundingScore(
        required_terms_present=all(
            _normalized(term) in normalized_response for term in expected_terms
        ),
        forbidden_terms_absent=all(
            _normalized(term) not in normalized_response for term in forbidden_terms
        ),
    )


def score_retrieval(
    ranked_ids: Sequence[str],
    relevant_ids: Sequence[str],
    k: int = 3,
) -> RetrievalScore:
    if k < 1:
        raise ValueError("k must be greater than zero.")
    relevant = set(relevant_ids)
    if not relevant:
        return RetrievalScore(recall_at_k=None, reciprocal_rank=0.0)

    top_k = ranked_ids[:k]
    recall_at_k = len(set(top_k) & relevant) / len(relevant)
    reciprocal_rank = next(
        (
            1.0 / rank
            for rank, document_id in enumerate(top_k, start=1)
            if document_id in relevant
        ),
        0.0,
    )
    return RetrievalScore(
        recall_at_k=recall_at_k,
        reciprocal_rank=reciprocal_rank,
    )


def summarize_retrieval(scores: Sequence[RetrievalScore]) -> RetrievalSummary:
    answerable = [score for score in scores if score.recall_at_k is not None]
    unanswerable_count = len(scores) - len(answerable)
    if not answerable:
        raise ValueError("Retrieval summary requires at least one answerable query.")
    return RetrievalSummary(
        recall_at_k=sum(score.recall_at_k for score in answerable) / len(answerable),
        mean_reciprocal_rank=sum(
            score.reciprocal_rank for score in answerable
        )
        / len(answerable),
        answerable_queries=len(answerable),
        unanswerable_queries=unanswerable_count,
    )
