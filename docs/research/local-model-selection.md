# Local model selection for RAGtaurant

> **Historical — obsolete.** This research documents an earlier evaluation; the current application uses Google Gemini and no longer includes the local evaluator. References to configuration, scripts and architecture describe the project at that time.

Research date: 2026-10-05

## Scope and observed context

Objective: select a local chat model and embedding model to answer in Spanish, call tools, and retrieve information from the menu and restaurant knowledge base.

Hardware observed on 2026-10-05: Intel Core Ultra 9 386H (16 logical CPUs), 23 GiB of RAM and an NVIDIA GeForce RTX 5070 Ti Laptop GPU with 12,227 MiB of VRAM. `nvidia-smi` detected the GPU on the host and inside the container; the laptop was not restarted. The inference service and all models ran in `ollama/ollama:latest` (Ollama 0.34.0), with Docker port 11434 published as host port 11435 to coexist with the native Ollama instance using 11434. The Compose backend continued to use the internal address `http://ollama:11434`.

The backend created the agent with `ChatOllama` and `bind_tools` ([runner](../../backend/app/rag/agent.py)) and used `OllamaEmbeddings` for indexing and querying ([embedding service](../../backend/app/rag/embeddings.py)). `get_weather_forecast` was part of `bot_tools` and was included in the evaluation ([available tools](../../backend/app/rag/tools.py)). The default configuration and Compose had been aligned on Qwen3 8B and BGE-M3; environment variables still allowed overrides ([configuration](../../backend/app/core/config.py)).

The local MongoDB contained five menu items and a 768-dimensional vector index corresponding to the previous embedding model. Selecting BGE-M3 required regenerating those vectors and updating the index to 1024 dimensions before starting the backend with the new configuration. There were no documents in the knowledge collection during this check.

## Comparison

Ollama sizes are the published artifact/tag sizes, not peak RAM usage or a speed guarantee. Actual memory use also depends on the context/KV cache, runtime and other workloads. The consulted sources do not provide comparable tokens-per-second figures for this processor on CPU.

| Candidate | Languages and tool calling | Published size/context | Assessment for this use case |
|---|---|---|---|
| **Qwen3 8B** (`qwen3:8b`) | Qwen claims support for more than 100 languages and agentic/tool-calling capabilities in thinking and non-thinking modes; the Ollama listing includes tool calling. This establishes stated compatibility, not a success rate for these tools. [1][2] | Ollama: 5.2 GB and 40K context. The upstream model card states 8.2B parameters, 32,768 native tokens and up to 131,072 with YaRN. [1][2] | Best initial candidate when prioritizing Spanish, instruction following and tool calls. The artifact fits within the nominal 24 GiB capacity, but CPU performance and peak memory must be measured. Thinking can add latency; test non-thinking mode for routine dialogue. |
| **Llama 3.2 3B Instruct** (`llama3.2`) | Meta lists Spanish among its eight officially supported languages and describes multilingual dialogue, agentic retrieval and tool use; Ollama marks the model as tool-compatible. The model card does not promise reliability for this project's tool schema. [3][4] | Ollama: 2.0 GB and 128K context. Meta describes 3.21B parameters; its model card also mentions quantized variants limited to 8K. [3][4] | A lightweight CPU alternative with potentially lower latency. It is substantially smaller than Qwen3 8B, so tool selection, argument extraction and consistency in Spanish should be checked before prioritizing speed. |
| **BGE-M3** (`bge-m3`) | Multilingual embedding model: BAAI claims support for more than 100 languages and offers dense, sparse and multi-vector retrieval. It is not a conversational LLM and does not perform tool calling. [5][6] | Ollama: 1.2 GB, 8K context. BAAI model card: 1024-dimensional dense vectors, maximum 8192 tokens. [5][6] | Recommended for Spanish menu and knowledge retrieval and queries with exact terms (dishes, ingredients, allergens). Ollama exposes the local embedding model; sparse/multi-vector support in the base model does not imply that the MongoDB pipeline used it. |
| **Nomic Embed Text v1.5** (`nomic-embed-text`) | The author's model card is tagged as English and does not claim multilingual support comparable to BGE-M3; do not assume Spanish retrieval quality without evaluation. It is an embedding encoder, not a chat model. [7][8] | Ollama: 274 MB and listed 2K context. The upstream model card describes 768 dimensions by default, Matryoshka dimensionality reduction and context extendable to 8192. [7][8] | Smaller, but less suitable as a first choice for Spanish text and questions. The model card requires `search_document:` and `search_query:` prefixes in its RAG examples; check the Ollama wrapper/template, as the project code sent text directly. The upstream advertised context differs from the Ollama package listing. |

## Recommendation

### Results measured in RAGtaurant

The complete matrix was run with the former `backend/scripts/evaluate_local_models.py` runner (removed after migration) and saved in [`docs/research/local-model-benchmark.json`](./local-model-benchmark.json). It used a 4096-token context, temperature 0, seed 0 and simulated tools without real writes.

#### Generation and tool calling

| Model | Hardware | Tool accuracy | Argument accuracy | Grounded response rate | Mean latency | Container peak | Working set | Peak VRAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3 8B | CPU | **0.9286** | **0.8571** | **0.5000** | 20.967 s | 14,981 MiB | 13,458 MiB | — |
| Llama 3.2 3B | CPU | **0.9286** | 0.5714 | 0.4286 | **12.474 s** | 12,661 MiB | 11,236 MiB | — |
| Qwen3 8B | GPU | **0.9286** | **0.8571** | **0.5000** | 3.711 s | **10,164 MiB** | **9,852 MiB** | **7,317 MiB** |
| Llama 3.2 3B | GPU | **0.9286** | 0.6429 | 0.3571 | **1.996 s** | 10,309 MiB | 10,292 MiB | 4,425 MiB |

Key observations:

- Both models failed the case with no evidence about dogs on the terrace. Qwen omitted forecasts for a past date and a date outside the forecast horizon; Llama made unnecessary tool calls in several cases.
- Qwen3 was more consistent at filling in correct arguments and accurately summarizing simulated reservation and weather results.
- Llama 3.2 was considerably faster, especially on GPU, but made more formatting/argument errors and several responses were less well grounded.
- These rates do not establish that the model can serve as a security boundary or source of truth. Although Qwen3 was selected as the default local agent, the “dogs are not allowed” result shows that institutional search requires deterministic evidence handling and that the model must not answer on its own when a tool provides no data. Do not consider the chatbot production-ready until that policy is enforced outside the model.

#### Retrieval

| Embedding | Hardware | Dimensions | Recall@3 | MRR@3 | False positive without evidence | Latency per input |
|---|---:|---:|---:|---:|---:|---:|
| BGE-M3 | CPU | **1024** | **0.8333** | **0.8333** | **No** | 592.98 ms |
| Nomic Embed Text | CPU | 768 | 0.7500 | 0.7222 | Yes | **220.23 ms** |
| BGE-M3 | GPU | **1024** | **0.8333** | **0.8333** | **No** | **225.84 ms** |
| Nomic Embed Text | GPU | 768 | 0.7500 | 0.7222 | Yes | 126.90 ms |

Key observations:

- **BGE-M3** outperformed the then-current embedding model in retrieval and avoided the false positive in the unanswered case (`¿Se admiten perros en la terraza?`).
- Both embeddings failed the synonym case `sopa fría de hortalizas`; this suggests expanding the indexed text or adding more examples/synonyms to the corpus.
- Nomic was faster on both hardware types, but sacrificed retrieval quality and produced a false positive without evidence.

### Final selection

The recommended local configuration for RAGtaurant was:

- **Default LLM:** `qwen3:8b`
- **Default embedding:** `bge-m3`
- **Vector index dimensions:** `1024`

Reasons:

1. Qwen3 8B had the best measured balance between argument accuracy and grounding; both models tied on tool selection.
2. Llama 3.2 3B is a reasonable fallback when latency is the overriding priority, but not as the default because it loses too much reliability in arguments and grounding.
3. BGE-M3 consistently outperformed the previous embedding model and eliminated the false positive in the unanswered case, justifying regeneration of all vectors.

For a smaller footprint, keep **Llama 3.2 3B + BGE-M3** documented for testing or more constrained machines. Nomic can remain a historical baseline, but not the default.

Changing embedding models requires **re-embedding every document** with the same model used for queries and checking/reconfiguring the vector index dimension (BGE-M3: 1024; Nomic v1.5: 768 by default). Do not mix old and new vectors. LangChain confirms that `ChatOllama.bind_tools()` binds tools, but also warns that compatibility depends on the Ollama model; the wrapper interface does not guarantee that each model will select the correct tool or produce correct arguments. [9][10]

## Further empirical evaluation

Before deciding on production use, run the same test set with both LLMs and BGE-M3 (and Nomic only as a comparison):

- Measure time to first token, total time and peak RAM on CPU, with representative history/context and expected concurrent queries.
- Measure `Recall@k`/`MRR` on Spanish questions phrased in different ways: dish names and synonyms, ingredients, allergens, dietary restrictions, prices and facts from `llm.txt`. Include queries without a correct answer in the corpus.
- Measure correct-tool rate, valid arguments, unnecessary calls and answers grounded in results; test reservation creation, lookup, editing and cancellation with incomplete date/time and missing identifiers. Use test data and avoid real side effects.
- Test natural Spanish responses and ambiguous and adversarial queries; check that prices, allergens and conditions are not invented when retrieval provides no evidence.
- After deciding, reindex with the selected embedding model and validate the MongoDB vector index dimension.

The official pages describe model families, capabilities and formats; they do not prove quality on the RAGtaurant menu or provide a reliable prediction of tokens per second for the Core Ultra 9 386H. That question remains open until evaluation on the restaurant's actual hardware and data.

## Primary sources

1. Ollama, [Qwen3 model library](https://ollama.com/library/qwen3) (tags, size, context, languages and tools).
2. Qwen, [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B) (parameters, context length, languages, agentic use and reasoning modes).
3. Ollama, [Llama 3.2 model library](https://ollama.com/library/llama3.2) (tags, size, context, languages and tools).
4. Meta, [Llama 3.2 3B Instruct model card](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) (languages, size, intended uses and limits/license).
5. Ollama, [BGE-M3 model library](https://ollama.com/library/bge-m3) (size, context, languages and advertised retrieval variants).
6. BAAI, [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3) (dimensions, maximum length, multilingualism and dense/sparse/multi-vector modes).
7. Ollama, [nomic-embed-text model library](https://ollama.com/library/nomic-embed-text) (size, Ollama context and use as an encoder).
8. Nomic AI, [nomic-embed-text-v1.5 model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) (dimensions, Matryoshka, context and search prefixes).
9. LangChain, [ChatOllama integration](https://docs.langchain.com/oss/python/integrations/chat/ollama) (tool calling via `bind_tools` and the compatible Ollama model requirement).
10. LangChain, [ChatOllama `bind_tools` API reference](https://reference.langchain.com/python/langchain-ollama/chat_models/ChatOllama/bind_tools) (signature, accepted formats and compatibility note).
11. Ollama, [Embeddings documentation](https://docs.ollama.com/capabilities/embeddings) (embedding usage and model-dependent dimensions).
