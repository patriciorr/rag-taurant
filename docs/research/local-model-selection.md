# Seleccion de modelos locales para RAGtaurant

Fecha de consulta: 2026-10-05

## Alcance y contexto observado

Objetivo: seleccionar una pareja local de modelo de chat y embeddings para responder en español, llamar herramientas y recuperar información de la carta y del conocimiento del restaurante, usando CPU en un Intel Core Ultra 9 386H, con aproximadamente 24 GiB de RAM disponibles y sin GPU visible. Los datos de hardware y disponibilidad de GPU son los indicados para esta evaluación; no se ejecutaron modelos ni pruebas de rendimiento.

El backend crea el agente con `ChatOllama` y `bind_tools` ([runner](../../backend/app/rag/agent.py)), y usa `OllamaEmbeddings` para indexar y consultar ([servicio de embeddings](../../backend/app/rag/embeddings.py)). Importante: el valor por defecto versionado de `OLLAMA_MODEL` es `deepseek-r1:14b`, no `llama3.2`; un `.env` o variable de entorno puede sobrescribirlo ([configuración](../../backend/app/core/config.py)). Además, el prompt menciona `get_weather_forecast`, pero esa herramienta no está en la lista `bot_tools` actualmente vinculada al modelo ([herramientas disponibles](../../backend/app/rag/tools.py)). Esto debe corregirse o excluirse de la evaluación del tool calling; el modelo no puede invocar una herramienta que no recibe.

## Comparación

Los tamaños de Ollama son el tamaño publicado del artefacto/tag, no el pico de RAM ni una garantía de velocidad. La memoria real también depende del contexto/KV cache, el runtime y las demás cargas. No hay una cifra de tokens por segundo comparable en las fuentes consultadas para este procesador en CPU.

| Candidato | Idiomas y tool calling | Tamaño/contexto publicado | Lectura para este caso |
|---|---|---|---|
| **Qwen3 8B** (`qwen3:8b`) | Qwen declara más de 100 idiomas y capacidades agentic/tool calling en modos thinking y non-thinking; la ficha Ollama incluye tool calling. Eso acredita compatibilidad declarada, no una tasa de éxito para estas herramientas. [1][2] | Ollama: 5.2 GB y contexto 40K. La ficha upstream indica 8.2B parámetros, 32,768 tokens nativos y hasta 131,072 con YaRN. [1][2] | Mejor candidato inicial si se prioriza español, seguimiento de instrucciones y llamadas de herramientas. El artefacto es viable en capacidad nominal frente a 24 GiB, pero el rendimiento en CPU y la memoria pico deben medirse. Thinking puede añadir latencia; probar modo no-thinking para diálogo rutinario. |
| **Llama 3.2 3B Instruct** (`llama3.2`) | Meta declara español entre sus ocho idiomas oficialmente soportados, y describe usos de diálogo multilingüe, retrieval agéntico y tool use; Ollama marca el modelo como compatible con tools. La ficha no promete fiabilidad para el esquema de herramientas de este proyecto. [3][4] | Ollama: 2.0 GB y contexto 128K. Meta describe 3.21B parámetros; su ficha menciona también variantes cuantizadas con límite de 8K. [3][4] | Alternativa ligera para CPU y menor latencia probable. Es un modelo bastante menor que Qwen3 8B, por lo que conviene comprobar especialmente selección de herramienta, extracción de argumentos y consistencia en español antes de priorizarlo por rapidez. |
| **BGE-M3** (`bge-m3`) | Embedding multilingüe: BAAI declara más de 100 idiomas y ofrece recuperación densa, sparse y multi-vector. No es un LLM conversacional ni realiza tool calling. [5][6] | Ollama: 1.2 GB, contexto 8K. Ficha BAAI: vectores densos de 1024 dimensiones, máximo 8192 tokens. [5][6] | Recomendación para recuperar carta/conocimiento en español y consultas con términos exactos (platos, ingredientes, alérgenos). Ollama expone el modelo de embedding local; su soporte sparse/multi-vector en el modelo base no implica que el pipeline MongoDB actual lo esté usando. |
| **Nomic Embed Text v1.5** (`nomic-embed-text`) | La ficha del autor aparece etiquetada como English y no declara soporte multilingüe comparable al de BGE-M3; no asumir calidad de recuperación en español sin evaluación. Es solo un encoder de embeddings, no un modelo de chat. [7][8] | Ollama: 274 MB y contexto listado de 2K. La ficha upstream describe 768 dimensiones por defecto, reducción Matryoshka y contexto ampliable hasta 8192. [7][8] | Más pequeño, pero menos apropiado como primera elección para texto y preguntas en español. La ficha requiere prefijos `search_document:` y `search_query:` en sus ejemplos de RAG; comprobar qué hace el wrapper/plantilla de Ollama, pues el código del proyecto envía los textos directamente. El contexto anunciado por la ficha upstream no coincide con el listado del paquete Ollama. |

## Recomendación

Empezar la evaluación con **Qwen3 8B + BGE-M3**. Sus atributos publicados se alinean mejor con el requisito principal: español/multilingüismo para generación y recuperación. Los artefactos publicados suman aproximadamente 6.4 GB; es una referencia de almacenamiento, no una estimación de RAM pico. Con 24 GiB disponibles parece razonable probarlos en el host sin GPU, reservando margen para el contexto, el proceso de aplicación y la base de datos. En CPU la latencia puede ser el factor limitante, especialmente con prompts/historial largos o generación en modo thinking; no se puede inferir el tiempo de respuesta a partir del tamaño del artefacto.

Como alternativa de menor huella, medir **Llama 3.2 3B + BGE-M3**; como paso intermedio, Ollama publica también `qwen3:4b` en 2.5 GB. La elección final depende del equilibrio medido entre latencia y corrección, no solo de la etiqueta de soporte de herramientas. Nomic puede servir como baseline pequeño, pero no reemplazaría BGE-M3 para el corpus español sin resultados que lo justifiquen.

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