#!/usr/bin/env python3
"""Run the versioned model evaluation against a local Ollama Docker service."""

import argparse
import json
import math
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LOCAL_OLLAMA_OPENER = build_opener(ProxyHandler({}))

from app.evaluation.local_model_benchmark import (
    DATASET_PATH,
    RetrievalScore,
    load_evaluation_cases,
    score_grounding,
    score_retrieval,
    score_tool_call,
    summarize_retrieval,
)


OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_menu",
            "description": "Busca platos en la carta usando sus atributos registrados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "vegan_only": {"type": "boolean"},
                    "vegetarian_only": {"type": "boolean"},
                    "exclude_allergens": {"type": "array", "items": {"type": "string"}},
                    "available_only": {"type": "boolean"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_info",
            "description": "Busca información institucional documentada del restaurante.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Consulta la previsión meteorológica del restaurante para una fecha.",
            "parameters": {
                "type": "object",
                "properties": {"date": {"type": "string", "format": "date"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_table_reservation",
            "description": "Prepara una reserva simulada; no realiza cambios reales.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "guests": {"type": "integer"},
                },
                "required": [
                    "customer_name",
                    "email",
                    "phone",
                    "date",
                    "time",
                    "guests",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_table_reservation",
            "description": "Consulta una reserva simulada con código y contacto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["reservation_id", "email", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_table_reservation",
            "description": "Prepara un cambio simulado; no modifica la reserva.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "guests": {"type": "integer"},
                },
                "required": ["reservation_id", "email", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_table_reservation",
            "description": "Prepara una cancelación simulada; no cancela la reserva.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["reservation_id", "email", "phone"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "Eres el asistente de RAGtaurant y respondes en español. Usa una herramienta "
    "cuando la consulta requiera datos del restaurante, carta, previsión o reservas. "
    "No inventes información; si la herramienta no aporta evidencia, dilo. "
    "Rechaza brevemente las peticiones ajenas al restaurante y no des consejos generales. "
    "Aunque las herramientas y sus resultados sean simulados, utiliza el resultado "
    "recibido como evidencia del caso y resume sus datos. Antes de una reserva, "
    "modificación o cancelación, explica que la operación sigue pendiente y pide "
    "confirmación. Nunca afirmes que esos cambios se han ejecutado. "
    "La fecha actual fija para esta evaluación es {reference_date}."
)


def request_json(
    base_url: str,
    path: str,
    body: Mapping[str, Any] | None = None,
    timeout: int = 300,
) -> tuple[dict[str, Any], float]:
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    start = time.perf_counter()
    try:
        with LOCAL_OLLAMA_OPENER.open(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Ollama request failed at {path}: {error}") from error
    return result, time.perf_counter() - start


def _validate_local_base_url(base_url: str) -> None:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1", "ollama"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Ollama base URL must point to a local service (localhost, loopback, "
            "or the Docker Compose service named 'ollama')."
        )


def _memory_usage_bytes(container_name: str) -> tuple[int, int]:
    current_result = subprocess.run(
        ["docker", "exec", container_name, "cat", "/sys/fs/cgroup/memory.current"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    stat_result = subprocess.run(
        ["docker", "exec", container_name, "cat", "/sys/fs/cgroup/memory.stat"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    memory_stats = {
        name: int(value)
        for line in stat_result.stdout.splitlines()
        if len(parts := line.split()) == 2
        for name, value in [parts]
    }
    if "inactive_file" not in memory_stats:
        raise RuntimeError("Ollama container has no cgroup inactive_file memory metric.")
    current = int(current_result.stdout.strip())
    working_set = max(0, current - memory_stats["inactive_file"])
    return current, working_set


def _gpu_memory_mib() -> int:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    values = [int(value.strip()) for value in result.stdout.splitlines() if value.strip()]
    if not values:
        raise RuntimeError("nvidia-smi did not report GPU memory.")
    return sum(values)


class ResourceMonitor:
    def __init__(
        self,
        container_name: str,
        track_gpu: bool,
        sample_interval: float = 0.5,
    ):
        self.container_name = container_name
        self.track_gpu = track_gpu
        self.sample_interval = sample_interval
        self.peak_container_memory = 0
        self.peak_container_working_set = 0
        self.peak_gpu_memory = 0
        self.failure: Exception | None = None
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def _sample_once(self) -> None:
        try:
            current, working_set = _memory_usage_bytes(self.container_name)
            self.peak_container_memory = max(self.peak_container_memory, current)
            self.peak_container_working_set = max(
                self.peak_container_working_set,
                working_set,
            )
            if self.track_gpu:
                self.peak_gpu_memory = max(
                    self.peak_gpu_memory,
                    _gpu_memory_mib(),
                )
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
            self.failure = error
            self.stop_event.set()

    def _sample(self) -> None:
        while not self.stop_event.is_set():
            self._sample_once()
            if self.failure is not None:
                return
            self.stop_event.wait(self.sample_interval)

    def __enter__(self) -> "ResourceMonitor":
        self._sample_once()
        if self.failure is not None:
            raise RuntimeError(f"Could not sample benchmark resources: {self.failure}")
        self.thread = threading.Thread(target=self._sample, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()
        if self.failure is not None:
            raise RuntimeError(f"Could not sample benchmark resources: {self.failure}")


def _tool_calls(message: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    calls = message.get("tool_calls", [])
    if not isinstance(calls, list):
        raise ValueError("Ollama returned tool_calls in an unexpected format.")
    return calls


def _chat_request(
    base_url: str,
    model: str,
    prompt: str,
    hardware: str,
    messages: Sequence[Mapping[str, Any]] | None = None,
    reference_date: str = "2026-10-05",
) -> tuple[dict[str, Any], float]:
    options: dict[str, Any] = {
        "temperature": 0,
        "seed": 0,
        "num_ctx": 4096,
        "num_predict": 160,
        "num_thread": 16,
    }
    if hardware == "cpu":
        options["num_gpu"] = 0
    return request_json(
        base_url,
        "/api/chat",
        {
            "model": model,
            "messages": list(messages)
            if messages is not None
            else [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(reference_date=reference_date),
                },
                {"role": "user", "content": prompt},
            ],
            "tools": OLLAMA_TOOLS if messages is None else [],
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": options,
        },
    )


def _unload_model(base_url: str, model: str) -> None:
    request_json(
        base_url,
        "/api/generate",
        {"model": model, "keep_alive": 0},
    )


def evaluate_generation_case(
    base_url: str,
    model: str,
    hardware: str,
    case: Mapping[str, Any],
    reference_date: str,
) -> dict[str, Any]:
    response, elapsed_seconds = _chat_request(
        base_url,
        model,
        case["prompt"],
        hardware,
        reference_date=reference_date,
    )
    message = response.get("message")
    if not isinstance(message, dict):
        raise ValueError(f"Ollama returned no assistant message for {case['id']}.")
    calls = _tool_calls(message)
    tool_score = score_tool_call(
        case["expected_tool"],
        calls,
        case["expected_arguments"],
        case.get("required_arguments", []),
        case.get("allowed_arguments"),
    )
    final_response = message.get("content", "")
    follow_up_seconds = 0.0

    if case.get("simulated_result") and tool_score.correct_tool:
        tool_name = calls[0]["function"]["name"]
        follow_up_messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(reference_date=reference_date),
            },
            {"role": "user", "content": case["prompt"]},
            {
                "role": "assistant",
                "content": final_response,
                "tool_calls": calls,
            },
            {
                "role": "tool",
                "tool_name": tool_name,
                "tool_call_id": calls[0].get("id"),
                "content": case["simulated_result"],
            },
        ]
        follow_up, follow_up_seconds = _chat_request(
            base_url,
            model,
            case["prompt"],
            hardware,
            follow_up_messages,
            reference_date,
        )
        follow_up_message = follow_up.get("message")
        if not isinstance(follow_up_message, dict):
            raise ValueError(f"Ollama returned no final answer for {case['id']}.")
        final_response = follow_up_message.get("content", "")

    grounding = score_grounding(
        final_response,
        case.get("expected_response_terms", []),
        case.get("forbidden_response_terms", []),
    )
    metrics = response.get("prompt_eval_count", 0), response.get("eval_count", 0)
    return {
        "id": case["id"],
        "correct_tool": tool_score.correct_tool,
        "valid_arguments": tool_score.valid_arguments,
        "grounded_response": grounding.grounded,
        "required_terms_present": grounding.required_terms_present,
        "forbidden_terms_absent": grounding.forbidden_terms_absent,
        "latency_seconds": round(elapsed_seconds + follow_up_seconds, 3),
        "tool_call_latency_seconds": round(elapsed_seconds, 3),
        "prompt_tokens": metrics[0],
        "generated_tokens": metrics[1],
        "tool_calls": calls,
        "response": final_response,
    }


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Embedding vectors must have the same non-zero dimension.")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("Ollama returned a zero-length embedding vector.")
    return dot / (left_norm * right_norm)


def evaluate_embeddings(
    base_url: str,
    model: str,
    hardware: str,
    dataset: Mapping[str, Any],
) -> dict[str, Any]:
    documents = dataset["documents"]
    queries = dataset["retrieval"]
    inputs = [document["text"] for document in documents] + [
        query["query"] for query in queries
    ]
    options: dict[str, Any] = {}
    if hardware == "cpu":
        options["num_gpu"] = 0
    result, elapsed_seconds = request_json(
        base_url,
        "/api/embed",
        {
            "model": model,
            "input": inputs,
            "truncate": False,
            "keep_alive": "10m",
            "options": options,
        },
    )
    vectors = result.get("embeddings")
    if (
        not isinstance(vectors, list)
        or len(vectors) != len(inputs)
        or not vectors
        or any(not isinstance(vector, list) for vector in vectors)
    ):
        raise ValueError(f"Ollama returned invalid embeddings for model {model}.")
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1 or not next(iter(dimensions)):
        raise ValueError(f"Ollama returned inconsistent embedding dimensions for {model}.")

    document_vectors = vectors[: len(documents)]
    query_vectors = vectors[len(documents) :]
    retrieval_results = []
    no_evidence_threshold = dataset["no_evidence_similarity_threshold"]
    for query, query_vector in zip(queries, query_vectors):
        similarities = [
            _cosine_similarity(query_vector, document_vector)
            for document_vector in document_vectors
        ]
        ranked = sorted(
            zip(documents, similarities),
            key=lambda item: item[1],
            reverse=True,
        )
        ranked_ids = [document["id"] for document, _ in ranked]
        score = score_retrieval(ranked_ids, query["relevant_ids"], k=3)
        retrieval_results.append(
            {
                "id": query["id"],
                "recall_at_3": score.recall_at_k,
                "reciprocal_rank": score.reciprocal_rank,
                "top_document_id": ranked[0][0]["id"],
                "top_similarity": round(ranked[0][1], 4),
                "false_positive": not query["relevant_ids"]
                and ranked[0][1] >= no_evidence_threshold,
            }
        )
    summary = summarize_retrieval(
        [
            RetrievalScore(
                recall_at_k=item["recall_at_3"],
                reciprocal_rank=item["reciprocal_rank"],
            )
            for item in retrieval_results
        ]
    )
    return {
        "model": model,
        "hardware": hardware,
        "dimensions": next(iter(dimensions)),
        "input_count": len(inputs),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "milliseconds_per_input": round(elapsed_seconds * 1000 / len(inputs), 2),
        "recall_at_3": round(summary.recall_at_k, 4),
        "mrr": round(summary.mean_reciprocal_rank, 4),
        "answerable_queries": summary.answerable_queries,
        "unanswerable_queries": summary.unanswerable_queries,
        "unanswerable_false_positive": any(
            item["false_positive"]
            for item in retrieval_results
            if item["recall_at_3"] is None
        ),
        "cases": retrieval_results,
    }


def _gpu_name() -> str:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    names = [name.strip() for name in result.stdout.splitlines() if name.strip()]
    if not names:
        raise RuntimeError("nvidia-smi did not report a GPU.")
    return ", ".join(names)


def _host_memory_total_bytes() -> int:
    with Path("/proc/meminfo").open(encoding="ascii") as meminfo:
        for line in meminfo:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("Could not find MemTotal in /proc/meminfo.")


def evaluate(
    base_url: str,
    models: Sequence[str],
    embedding_models: Sequence[str],
    hardware_profiles: Sequence[str],
    container_name: str,
) -> dict[str, Any]:
    _validate_local_base_url(base_url)
    dataset = load_evaluation_cases()
    ollama_version, _ = request_json(base_url, "/api/version")
    gpu_name = _gpu_name() if "gpu" in hardware_profiles else None
    runs = []
    for hardware in hardware_profiles:
        for model in models:
            print(f"Generation/tool evaluation: {hardware} / {model}", flush=True)
            with ResourceMonitor(
                container_name,
                track_gpu=hardware == "gpu",
            ) as resources:
                generation_cases = []
                for case in dataset["generation"]:
                    print(f"  case: {case['id']}", flush=True)
                    generation_cases.append(
                        evaluate_generation_case(
                            base_url,
                            model,
                            hardware,
                            case,
                            dataset["reference_date"],
                        )
                    )
                _unload_model(base_url, model)
            runs.append(
                {
                    "kind": "generation_and_tools",
                    "model": model,
                    "hardware": hardware,
                    "peak_container_memory_mib": round(
                        resources.peak_container_memory / (1024 * 1024), 1
                    ),
                    "peak_container_working_set_mib": round(
                        resources.peak_container_working_set / (1024 * 1024), 1
                    ),
                    "peak_gpu_memory_mib": resources.peak_gpu_memory
                    if hardware == "gpu"
                    else None,
                    "cases": generation_cases,
                    "tool_accuracy": round(
                        sum(case["correct_tool"] for case in generation_cases)
                        / len(generation_cases),
                        4,
                    ),
                    "argument_accuracy": round(
                        sum(case["valid_arguments"] for case in generation_cases)
                        / len(generation_cases),
                        4,
                    ),
                    "grounded_response_rate": round(
                        sum(case["grounded_response"] for case in generation_cases)
                        / len(generation_cases),
                        4,
                    ),
                    "mean_latency_seconds": round(
                        sum(case["latency_seconds"] for case in generation_cases)
                        / len(generation_cases),
                        3,
                    ),
                }
            )
        for model in embedding_models:
            print(f"Embedding/retrieval evaluation: {hardware} / {model}", flush=True)
            with ResourceMonitor(
                container_name,
                track_gpu=hardware == "gpu",
            ) as resources:
                embedding_result = evaluate_embeddings(
                    base_url,
                    model,
                    hardware,
                    dataset,
                )
                _unload_model(base_url, model)
            embedding_result.update(
                {
                    "kind": "retrieval",
                    "peak_container_memory_mib": round(
                        resources.peak_container_memory / (1024 * 1024), 1
                    ),
                    "peak_container_working_set_mib": round(
                        resources.peak_container_working_set / (1024 * 1024), 1
                    ),
                    "peak_gpu_memory_mib": resources.peak_gpu_memory
                    if hardware == "gpu"
                    else None,
                }
            )
            runs.append(embedding_result)
    return {
        "dataset": str(DATASET_PATH.relative_to(DATASET_PATH.parents[1])),
        "dataset_version": dataset["version"],
        "reference_date": dataset["reference_date"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": {
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "memory_total_mib": round(_host_memory_total_bytes() / (1024 * 1024)),
            "gpu": gpu_name,
        },
        "ollama": {
            "version": ollama_version.get("version"),
            "container": container_name,
            "base_url": base_url,
            "num_ctx": 4096,
            "temperature": 0,
        },
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:11435")
    parser.add_argument("--container", default="ollama_restaurant")
    parser.add_argument("--models", default="qwen3:8b,llama3.2:latest")
    parser.add_argument("--embedding-models", default="bge-m3,nomic-embed-text")
    parser.add_argument("--hardware", default="cpu,gpu", choices=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    hardware_profiles = [value.strip() for value in args.hardware.split(",") if value.strip()]
    if not hardware_profiles or any(value not in {"cpu", "gpu"} for value in hardware_profiles):
        parser.error("--hardware must be a comma-separated list containing cpu and/or gpu.")
    if "gpu" in hardware_profiles:
        _gpu_name()

    result = evaluate(
        args.base_url,
        [value.strip() for value in args.models.split(",") if value.strip()],
        [value.strip() for value in args.embedding_models.split(",") if value.strip()],
        hardware_profiles,
        args.container,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Evaluation results written to {args.output}")


if __name__ == "__main__":
    main()
