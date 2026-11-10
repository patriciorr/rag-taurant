#!/usr/bin/env python3
"""Run a small, isolated, billable evaluation of the two candidate models."""

import asyncio
import json
import math
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.genai import types
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.core.init_db import INITIAL_MENU
from app.service.menu import menu_embedding_text

CHAT_MODEL = "gemini-3.8-flash"
EMBEDDING_MODEL = "gemini-embedding-2"
DIMENSIONS = 1536
CASES = (
    ("¿Cuánto cuesta el gazpacho?", "1"),
    ("¿Qué vino blanco recomiendas con pescado?", "16"),
    ("¿Qué alérgenos contiene la cerveza de cebada?", "18"),
)


def document_text(item: dict) -> str:
    return f"title: {item['name']} | text: {menu_embedding_text(item)}"


def query_text(query: str) -> str:
    return f"task: question answering | query: {query}"


async def embed_texts(service, texts: list[str]) -> list[list[float]]:
    result = await service.client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[{"parts": [{"text": text}]} for text in texts],
        config=types.EmbedContentConfig(output_dimensionality=DIMENSIONS),
    )
    vectors = [list(embedding.values) for embedding in result.embeddings]
    if len(vectors) != len(texts) or any(len(vector) != DIMENSIONS for vector in vectors):
        raise ValueError("The embedding response has an unexpected count or dimension.")
    return vectors


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Cannot compare embeddings with different dimensions.")
    denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    if denominator == 0:
        raise ValueError("Cannot compare a zero-length embedding.")
    return sum(x * y for x, y in zip(left, right)) / denominator


@tool
def search_menu(query: str) -> str:
    """Busca información de la carta para responder a una consulta."""
    raise RuntimeError("The evaluator supplies the retrieved context directly.")


async def evaluate() -> dict:
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is required.")

    embedder = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL, google_api_key=settings.GOOGLE_API_KEY
    )
    chat = ChatGoogleGenerativeAI(
        model=CHAT_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        thinking_level="medium",
        temperature=None,
        retries=0,
    ).bind_tools([search_menu])
    start = time.monotonic()
    documents = await embed_texts(embedder, [document_text(item) for item in INITIAL_MENU])
    queries = await embed_texts(embedder, [query_text(query) for query, _ in CASES])
    rankings = [
        sorted(
            zip(INITIAL_MENU, documents),
            key=lambda pair: cosine(query_vector, pair[1]),
            reverse=True,
        )
        for query_vector in queries
    ]
    for (query, expected_id), ranked in zip(CASES, rankings):
        top_ids = [item["id"] for item, _ in ranked[:3]]
        print(
            json.dumps({"query": query, "expected_id": expected_id, "top_3_ids": top_ids}, ensure_ascii=False),
            file=sys.stderr,
            flush=True,
        )
    results = []
    for (query, expected_id), ranked in zip(CASES, rankings):
        messages = [
            SystemMessage(content="Responde en español, de forma concisa. Consulta siempre search_menu antes de responder y usa solo la información recuperada."),
            HumanMessage(content=query),
        ]
        response = await chat.ainvoke(messages)
        calls = response.tool_calls
        answer = None
        if calls:
            if any(call["name"] != "search_menu" for call in calls):
                raise ValueError("The model requested an unexpected tool.")
            messages.append(response)
            context = "\n".join(menu_embedding_text(item) for item, _ in ranked[:3])
            for call in calls:
                messages.append(ToolMessage(content=context, tool_call_id=call["id"]))
            response = await chat.ainvoke(messages)
            if response.tool_calls:
                raise ValueError("The model requested additional tools after receiving context.")
            answer = response.text
        top_ids = [item["id"] for item, _ in ranked[:3]]
        results.append({
            "query": query,
            "expected_id": expected_id,
            "top_3_ids": top_ids,
            "retrieved_expected": expected_id in top_ids,
            "used_search_tool": bool(calls),
            "answer": answer,
        })
    return {
        "chat_model": CHAT_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "dimensions": DIMENSIONS,
        "thinking_level": "medium",
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(evaluate()), ensure_ascii=False, indent=2))
