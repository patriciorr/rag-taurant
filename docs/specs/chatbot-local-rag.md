# Chatbot local para RAGtaurant

## Problem Statement

El chatbot actual combina RAG, llamadas a herramientas, historial de conversación y operaciones de reserva en un flujo difícil de controlar. Algunas herramientas acceden directamente a MongoDB, omitiendo las reglas de autorización de la API; la previsión meteorológica no está conectada al agente; y las respuestas dependen demasiado de que el modelo siga instrucciones para no inventar datos o ejecutar cambios sin confirmación. El cliente necesita un asistente fiable, limitado a las tareas del restaurante y coherente con las reglas de carta, tiempo y reservas.

## Solution

Refactorizar el chatbot de React/FastAPI para responder en español únicamente con fuentes autorizadas del restaurante, los resultados de Open-Meteo y la API de reservas. Usar tools pequeñas con límites claros, recuperar datos estructurados de carta para dietas/alérgenos, validar de forma determinista las operaciones de reserva y exigir confirmación antes de cualquier mutación. Mantener Ollama y el procesamiento del chatbot local; Open-Meteo requiere conexión a internet.

El chatbot atenderá información del restaurante, carta, alergias y dietas, previsión meteorológica y creación, consulta, modificación y cancelación de reservas. Las respuestas sin evidencia suficiente y las peticiones fuera de ese ámbito se rechazarán de forma clara. Las conversaciones estarán aisladas por pestaña y no se persistirán de forma permanente.

## User Stories

1. Como cliente, quiero preguntar en español por la ubicación, horarios y servicios del restaurante, para planificar mi visita con información fiable.
2. Como cliente, quiero que el asistente consulte solo fuentes autorizadas del restaurante, para no recibir datos inventados o genéricos.
3. Como cliente, quiero que el asistente reconozca cuando no encuentra una respuesta, para poder verificar el dato por otra vía.
4. Como cliente, quiero que el asistente decline consultas ajenas al restaurante, para que el chatbot mantenga un propósito claro.
5. Como cliente, quiero buscar platos por nombre, ingredientes, categoría y precio, para encontrar opciones adecuadas.
6. Como cliente vegetariano o vegano, quiero que los resultados usen las etiquetas dietéticas registradas en la carta, para no depender de inferencias del modelo.
7. Como cliente con alergias, quiero filtrar platos usando los alérgenos explícitos de cada elemento de la carta, para identificar opciones con información verificable.
8. Como cliente con alergias, quiero que el asistente no garantice ausencia de contaminación cruzada cuando ese dato no conste, para entender los límites de la información disponible.
9. Como cliente, quiero preguntar por el tiempo de los próximos días, para planificar una visita al restaurante.
10. Como cliente, quiero preguntar por una fecha concreta y recibir previsión solo si esa fecha está entre hoy y los 13 días siguientes, para no confundir previsiones disponibles con predicciones inventadas.
11. Como cliente con una reserva verificada en la conversación, quiero preguntar por el tiempo del día de esa reserva sin volver a indicar la fecha, para obtener una respuesta contextual.
12. Como cliente, quiero crear una reserva indicando nombre, email, teléfono, fecha, hora y comensales, para reservar una mesa conversando con el asistente.
13. Como cliente, quiero modificar la fecha, hora o número de comensales de mi reserva, para actualizar mi visita sin crear otra reserva.
14. Como cliente, quiero consultar una reserva proporcionando su código, email y teléfono, para revisar sus datos sin exponer reservas de otras personas.
15. Como cliente, quiero cancelar una reserva verificada, para liberar mi mesa cuando no pueda asistir.
16. Como cliente, quiero que el asistente resuma los datos de una creación, modificación o cancelación y espere mi confirmación explícita, para evitar cambios accidentales.
17. Como cliente, quiero reservar de nuevo para el mismo día después de cancelar, para poder cambiar de planes sin perder la posibilidad de asistir.
18. Como cliente, quiero que mis reservas se acepten únicamente entre hoy y los 13 días siguientes, en intervalos de 30 minutos entre las 12:00 y las 23:00, para reservar en horarios válidos.
19. Como cliente, quiero que cada pestaña tenga una conversación aislada, para que mi historial no se mezcle con el de otra persona.
20. Como cliente, quiero que el contexto conversacional no se guarde permanentemente, para limitar la retención de mis mensajes.
21. Como operador del proyecto, quiero elegir el LLM y los embeddings a partir de mediciones locales de calidad, latencia y memoria, para equilibrar precisión y recursos de hardware.
22. Como operador del proyecto, quiero poder evaluar el modelo con CPU y con la GPU NVIDIA RTX 5070 Ti de 12 GB cuando vuelva a estar disponible, para comparar ambos modos sin requerir un reinicio como parte del trabajo.

## Implementation Decisions

- Mantener Ollama, el LLM y el almacenamiento del historial del chat en el entorno local. La llamada a Open-Meteo es externa y necesita internet.
- Evaluar inicialmente Qwen3 8B para generación y tool calling con BGE-M3 para embeddings multilingües. Comparar con Llama 3.2 3B como alternativa de menor huella; no fijar la selección definitiva sin benchmark en el hardware y datos del restaurante.
- Una sustitución del modelo de embeddings requiere regenerar todos los vectores con el mismo modelo que atiende las consultas y alinear la dimensión del índice vectorial. Los candidatos de la evaluación tienen dimensiones distintas.
- Mantener el LLM como coordinador conversacional, no como autoridad de los datos. El menú y las restricciones dietéticas/alérgenos deben comprobarse usando atributos estructurados de la carta; el RAG de información institucional debe responder solo con contenido recuperado.
- Limitar el agente a herramientas explícitas de búsqueda de carta, información del restaurante, previsión y operaciones de reservas. No permitir tareas generales ni acceso libre a la base de datos.
- Las herramientas de reserva deben reutilizar las reglas del servicio de reservas y no consultar ni mutar MongoDB directamente. El acceso a una reserva existente requiere su código, email y teléfono coincidentes.
- Tratar la confirmación como una condición aplicada por el backend, no solo como una instrucción del prompt. Antes de crear, modificar o cancelar, el chatbot presenta un resumen; no debe producirse ninguna mutación hasta recibir una respuesta afirmativa para esa acción pendiente.
- La reserva comprende nombre, email, teléfono, fecha, hora y comensales. Las modificaciones permitidas son fecha, hora y comensales; los datos de contacto y el nombre no se cambian desde el chatbot.
- La fecha de reserva se valida en la zona horaria del restaurante: desde hoy (día 1) hasta hoy + 13 días (día 14), inclusive. Para el día actual, la hora debe seguir disponible. Las horas válidas son cada media hora desde las 12:00 hasta las 23:00, inclusive.
- Cancelar conserva la reserva con estado cancelado. Solo las reservas activas bloquean otra reserva de los mismos contactos para el mismo día; por tanto, se puede volver a reservar ese día. La política de retención de datos cancelados deberá definirse antes de una puesta en producción con clientes reales.
- La previsión usa la ubicación configurada del restaurante y consulta un horizonte de 14 días. El bot puede responder por una fecha explícita dentro del horizonte, por los próximos días o por el día de una reserva identificada y verificada en la conversación. No informa fechas pasadas ni fechas fuera del horizonte; errores o falta de disponibilidad de Open-Meteo se comunican sin inventar valores.
- Generar un identificador aleatorio por pestaña para el historial. El historial será efímero y no se guardará permanentemente; el reinicio del backend lo elimina.
- Mantener el widget de chat existente como interfaz. No se incluye una experiencia independiente de gestión de reservas.

## Testing Decisions

- Probar comportamiento observable, no detalles internos del agente: respuesta final, rechazo por falta de evidencia o petición fuera de alcance, herramientas seleccionadas y estado real de las reservas.
- Usar el límite HTTP del chat como principal seam de integración. Sustituir Ollama, Open-Meteo y demás proveedores externos por dobles deterministas; verificar que la misma conversación conserva el estado de confirmación sin persistirlo.
- Añadir casos para carta y preguntas institucionales con y sin evidencia; respuestas dietéticas/alérgenos basadas en datos estructurados; previsión de hoy, límite del día 14, fecha pasada, fecha fuera de horizonte y fallo del proveedor.
- Probar creación, consulta, modificación y cancelación de reservas; autorización con código/email/teléfono; solicitud de confirmación; ausencia de mutación antes del sí; validaciones de ventana y media hora; y nueva reserva para el mismo día después de cancelar.
- Extender los tests de modelos y servicios de reserva existentes y los tests de contratos API para el nuevo comportamiento de cancelación e índices. Añadir integración con Mongo real para verificar unicidad de reservas activas y re-reserva tras cancelar, con el estilo de las pruebas de integración existentes.
- Añadir pruebas de frontend para aislamiento de sesión por pestaña, continuidad conversacional y renderizado de la solicitud/respuesta de confirmación. El proyecto no tiene actualmente un framework de tests frontend configurado.
- Evaluar candidatos de LLM y embeddings fuera de CI con un conjunto versionado de preguntas españolas sobre los datos reales del restaurante. Medir corrección de tool calling, fundamentación, recuperación, latencia y memoria en CPU y, cuando esté disponible, en GPU; incluir consultas sin respuesta y no ejecutar mutaciones reales.

## Out of Scope

- Respuestas en idiomas distintos del español.
- Consultas generales ajenas al restaurante, navegación web libre o fuentes no autorizadas.
- Garantías médicas o de ausencia de contaminación cruzada no respaldadas por la información del restaurante.
- Autenticación fuerte mediante contraseña de un solo uso, SMS, email u otro proveedor; las operaciones existentes se protegen con código/email/teléfono.
- Persistencia permanente de conversaciones o sincronización del historial entre pestañas/dispositivos.
- Una interfaz de reservas independiente del chatbot.
- Despliegue cloud, inferencia remota o cambio de proveedor fuera de Ollama.

## Further Notes

- El servicio actual de Open-Meteo devuelve siete días y debe exponer las 14 fechas necesarias.
- El agente actual enlaza tools directamente y las herramientas de reserva acceden directamente a MongoDB; deben migrarse para respetar las reglas compartidas.
- El repositorio contiene un valor por defecto de LLM y otro valor en Docker Compose; la configuración debe quedar coherente y el modelo efectivo debe documentarse.
- Docker Compose solicita una GPU NVIDIA. Durante esta sesión `nvidia-smi` no detecta el dispositivo, aunque el usuario confirma que el portátil dispone de una RTX 5070 Ti de 12 GB desactivada temporalmente. No se reiniciará el equipo ni se exigirá que la GPU esté activa para continuar.
- Esta especificación está aprobada en conversación; el GitHub Issue asociado es la referencia para su ejecución y seguimiento.
