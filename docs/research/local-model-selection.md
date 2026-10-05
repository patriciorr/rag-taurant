# Seleccion de modelos locales para RAGtaurant

Fecha de consulta: 2026-10-05

## Alcance y contexto observado

Objetivo: seleccionar una pareja local de modelo de chat y embeddings para responder en español, llamar herramientas y recuperar información de la carta y del conocimiento del restaurante.

Hardware observado el 2026-10-05: Intel Core Ultra 9 386H (16 CPU lógicas), 23 GiB de RAM y NVIDIA GeForce RTX 5070 Ti Laptop GPU con 12.227 MiB de VRAM. `nvidia-smi` detecta la GPU en el host y dentro del contenedor; no se reinició el portátil. El servicio de inferencia y todos los modelos se ejecutan en `ollama/ollama:latest` (Ollama 0.34.0), con el puerto Docker 11434 publicado como 11435 en el host para coexistir con el Ollama nativo que ocupa 11434. El backend en Compose sigue usando la dirección interna `http://ollama:11434`.

El backend crea el agente con `ChatOllama` y `bind_tools` ([runner](../../backend/app/rag/agent.py)), y usa `OllamaEmbeddings` para indexar y consultar ([servicio de embeddings](../../backend/app/rag/embeddings.py)). `get_weather_forecast` sí forma parte de `bot_tools` y se incluye en la evaluación ([herramientas disponibles](../../backend/app/rag/tools.py)). La configuración por defecto y Compose se han alineado en Qwen3 8B y BGE-M3; las variables de entorno aún permiten sobrescribirlos ([configuración](../../backend/app/core/config.py)).

El MongoDB local contiene cinco platos de la carta y un índice vectorial de 768 dimensiones, correspondiente al embedding anterior. La selección de BGE-M3 exige regenerar esos vectores y actualizar el índice a 1024 dimensiones antes de arrancar el backend con la nueva configuración. No había documentos en la colección de conocimiento durante esta comprobación.

## Comparación

Los tamaños de Ollama son el tamaño publicado del artefacto/tag, no el pico de RAM ni una garantía de velocidad. La memoria real también depende del contexto/KV cache, el runtime y las demás cargas. No hay una cifra de tokens por segundo comparable en las fuentes consultadas para este procesador en CPU.

| Candidato | Idiomas y tool calling | Tamaño/contexto publicado | Lectura para este caso |
|---|---|---|---|
| **Qwen3 8B** (`qwen3:8b`) | Qwen declara más de 100 idiomas y capacidades agentic/tool calling en modos thinking y non-thinking; la ficha Ollama incluye tool calling. Eso acredita compatibilidad declarada, no una tasa de éxito para estas herramientas. [1][2] | Ollama: 5.2 GB y contexto 40K. La ficha upstream indica 8.2B parámetros, 32,768 tokens nativos y hasta 131,072 con YaRN. [1][2] | Mejor candidato inicial si se prioriza español, seguimiento de instrucciones y llamadas de herramientas. El artefacto es viable en capacidad nominal frente a 24 GiB, pero el rendimiento en CPU y la memoria pico deben medirse. Thinking puede añadir latencia; probar modo no-thinking para diálogo rutinario. |
| **Llama 3.2 3B Instruct** (`llama3.2`) | Meta declara español entre sus ocho idiomas oficialmente soportados, y describe usos de diálogo multilingüe, retrieval agéntico y tool use; Ollama marca el modelo como compatible con tools. La ficha no promete fiabilidad para el esquema de herramientas de este proyecto. [3][4] | Ollama: 2.0 GB y contexto 128K. Meta describe 3.21B parámetros; su ficha menciona también variantes cuantizadas con límite de 8K. [3][4] | Alternativa ligera para CPU y menor latencia probable. Es un modelo bastante menor que Qwen3 8B, por lo que conviene comprobar especialmente selección de herramienta, extracción de argumentos y consistencia en español antes de priorizarlo por rapidez. |
| **BGE-M3** (`bge-m3`) | Embedding multilingüe: BAAI declara más de 100 idiomas y ofrece recuperación densa, sparse y multi-vector. No es un LLM conversacional ni realiza tool calling. [5][6] | Ollama: 1.2 GB, contexto 8K. Ficha BAAI: vectores densos de 1024 dimensiones, máximo 8192 tokens. [5][6] | Recomendación para recuperar carta/conocimiento en español y consultas con términos exactos (platos, ingredientes, alérgenos). Ollama expone el modelo de embedding local; su soporte sparse/multi-vector en el modelo base no implica que el pipeline MongoDB actual lo esté usando. |
| **Nomic Embed Text v1.5** (`nomic-embed-text`) | La ficha del autor aparece etiquetada como English y no declara soporte multilingüe comparable al de BGE-M3; no asumir calidad de recuperación en español sin evaluación. Es solo un encoder de embeddings, no un modelo de chat. [7][8] | Ollama: 274 MB y contexto listado de 2K. La ficha upstream describe 768 dimensiones por defecto, reducción Matryoshka y contexto ampliable hasta 8192. [7][8] | Más pequeño, pero menos apropiado como primera elección para texto y preguntas en español. La ficha requiere prefijos `search_document:` y `search_query:` en sus ejemplos de RAG; comprobar qué hace el wrapper/plantilla de Ollama, pues el código del proyecto envía los textos directamente. El contexto anunciado por la ficha upstream no coincide con el listado del paquete Ollama. |

## Recomendación

### Resultados medidos en RAGtaurant

La matriz completa se ejecutó con el runner versionado [`backend/scripts/evaluate_local_models.py`](../../backend/scripts/evaluate_local_models.py) y quedó guardada en [`docs/research/local-model-benchmark.json`](./local-model-benchmark.json). Se usó un contexto de 4096 tokens, temperatura 0, semilla 0 y herramientas simuladas sin escrituras reales.

#### Generación y tool calling

| Modelo | Hardware | Tool accuracy | Argument accuracy | Grounded response rate | Latencia media | Pico contenedor | Working set | Pico VRAM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3 8B | CPU | 0.8889 | **0.7778** | **0.6667** | 18.938 s | 12,655 MiB | 6,999 MiB | — |
| Llama 3.2 3B | CPU | 0.8889 | 0.4444 | 0.5556 | **10.525 s** | 11,417 MiB | **3,990 MiB** | — |
| Qwen3 8B | GPU | 0.8889 | **0.7778** | **0.5556** | 4.184 s | 11,170 MiB | 6,791 MiB | **7,041 MiB** |
| Llama 3.2 3B | GPU | 0.8889 | 0.5556 | 0.4444 | **1.961 s** | **10,745 MiB** | 8,355 MiB | 4,117 MiB |

Observaciones relevantes:

- Ambos modelos fallaron el caso sin evidencia sobre perros en la terraza: no rechazaron con la respuesta correcta basada en falta de evidencia.
- Qwen3 fue más consistente al rellenar argumentos correctos y al resumir correctamente los resultados simulados de reservas y meteorología.
- Llama 3.2 fue bastante más rápido, especialmente en GPU, pero cometió más errores de formato/argumentos y varias respuestas quedaron peor fundamentadas.

#### Recuperación

| Embedding | Hardware | Dimensiones | Recall@3 | MRR | Falso positivo sin evidencia | Latencia por input |
|---|---:|---:|---:|---:|---:|---:|
| BGE-M3 | CPU | **1024** | **0.8333** | **0.8667** | **No** | 276.66 ms |
| Nomic Embed Text | CPU | 768 | 0.7500 | 0.7639 | Sí | **79.97 ms** |
| BGE-M3 | GPU | **1024** | **0.8333** | **0.8667** | **No** | **263.30 ms** |
| Nomic Embed Text | GPU | 768 | 0.7500 | 0.7639 | Sí | 507.96 ms |

Observaciones relevantes:

- **BGE-M3** supera al embedding actual en recuperación y evita el falso positivo del caso sin respuesta (`¿Se admiten perros en la terraza?`).
- Ambos embeddings suspendieron el caso de sinónimo `sopa fría de hortalizas`; esto indica que conviene ampliar los textos indexados o añadir más ejemplos/sinónimos al corpus.
- En CPU, Nomic es claramente más rápido, pero sacrifica recuperación y genera un falso positivo sin evidencia. En GPU, además, BGE-M3 resulta incluso más rápido que Nomic en esta máquina.

### Selección final

La configuración local recomendada para RAGtaurant queda en:

- **LLM por defecto:** `qwen3:8b`
- **Embedding por defecto:** `bge-m3`
- **Dimensión del índice vectorial:** `1024`

Motivos:

1. Qwen3 8B fue el mejor equilibrio medido entre precisión de herramientas, validez de argumentos y fundamentación, tanto en CPU como en GPU.
2. Llama 3.2 3B es un fallback razonable cuando la prioridad absoluta es la latencia, pero no para la configuración por defecto porque pierde demasiada fiabilidad en argumentos y grounding.
3. BGE-M3 superó de forma consistente al embedding previo y eliminó el falso positivo del caso sin evidencia, por lo que justifica regenerar todos los vectores.

Como alternativa de menor huella, mantener documentado **Llama 3.2 3B + BGE-M3** para pruebas o equipos más ajustados. Nomic puede permanecer como baseline histórico, pero no como valor por defecto.

Cambiar de embeddings obliga a **re-embedir todos los documentos** con el mismo modelo que se usará en las consultas y a comprobar/reconfigurar la dimensión del índice vectorial (BGE-M3: 1024; Nomic v1.5: 768 por defecto). No mezclar vectores antiguos y nuevos. LangChain confirma que `ChatOllama.bind_tools()` enlaza herramientas, pero también advierte que la compatibilidad depende del modelo Ollama; la interfaz del wrapper no garantiza que cada modelo elija la herramienta o produzca argumentos correctos. [9][10]

## Evaluación empírica necesaria

Antes de decidir producción, ejecutar el mismo conjunto de pruebas con ambos LLM y BGE-M3 (y Nomic solo como comparación):

- Medir latencia hasta primer token, tiempo total y RAM pico en CPU, con historial/contextos representativos y consultas concurrentes previstas.
- Medir recuperación `Recall@k`/`MRR` sobre preguntas españolas redactadas de varias formas: nombres y sinónimos de platos, ingredientes, alérgenos, restricciones dietéticas, precios y hechos de `llm.txt`. Incluir consultas sin respuesta correcta en el corpus.
- Medir tasa de herramienta correcta, argumentos válidos, llamadas innecesarias y respuestas sustentadas por el resultado; probar creación, consulta, edición y cancelación de reservas con casos de fecha/hora incompletas y con identificador ausente. Usar datos de prueba y evitar efectos reales.
- Probar respuestas en castellano natural, consultas ambiguas y adversariales; verificar que precios, alérgenos y condiciones nunca se inventan cuando la recuperación no aporta evidencia.
- Tras una decisión, reindexar con el embedding seleccionado y validar la dimensión del vector index en MongoDB.

Las páginas oficiales describen familias, capacidades y formatos; no prueban calidad en la carta de RAGtaurant ni proporcionan una predicción fiable de tokens por segundo para el Core Ultra 9 386H. Esa parte queda abierta hasta ejecutar la evaluación en el hardware y datos reales del restaurante.

## Fuentes primarias

1. Ollama, [Qwen3 model library](https://ollama.com/library/qwen3) (tags, tamaño, contexto, idiomas y tools).
2. Qwen, [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B) (parámetros, context length, idiomas, agentic use y modos de razonamiento).
3. Ollama, [Llama 3.2 model library](https://ollama.com/library/llama3.2) (tags, tamaño, contexto, idiomas y tools).
4. Meta, [Llama 3.2 3B Instruct model card](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) (idiomas, tamaño, usos previstos y límites/licencia).
5. Ollama, [BGE-M3 model library](https://ollama.com/library/bge-m3) (tamaño, contexto, idiomas y variantes de recuperación anunciadas).
6. BAAI, [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3) (dimensiones, longitud máxima, multilingüismo y modos dense/sparse/multi-vector).
7. Ollama, [nomic-embed-text model library](https://ollama.com/library/nomic-embed-text) (tamaño, contexto de Ollama y uso como encoder).
8. Nomic AI, [nomic-embed-text-v1.5 model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) (dimensiones, Matryoshka, contexto y prefijos para búsqueda).
9. LangChain, [ChatOllama integration](https://docs.langchain.com/oss/python/integrations/chat/ollama) (tool calling mediante `bind_tools` y condición de modelo Ollama compatible).
10. LangChain, [ChatOllama `bind_tools` API reference](https://reference.langchain.com/python/langchain-ollama/chat_models/ChatOllama/bind_tools) (firma, formatos aceptados y nota de compatibilidad).
11. Ollama, [Embeddings documentation](https://docs.ollama.com/capabilities/embeddings) (uso de embeddings y dimensión dependiente del modelo).