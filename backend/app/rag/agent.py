# app/rag/agent.py
import unicodedata
import logging
from typing import Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from app.core.config import settings
from app.core.exceptions import (
    DatabaseException,
    ReservationConflictException,
    ReservationNotFoundException,
    ReservationValidationException,
)
from app.models.reservation import ReservationContact, ReservationCreate, ReservationUpdate
from pydantic import ValidationError
from app.rag.tools import (
    bot_tools,
    format_verified_table_reservation,
    format_reservation_confirmation,
    get_verified_table_reservation,
    format_table_reservation_update,
    prepare_table_reservation,
    prepare_table_reservation_update,
)
from app.service.reservation import reservation_service

logger = logging.getLogger(__name__)

# 1. Mapa de herramientas por nombre para invocación directa
TOOLS_MAP = {tool.name: tool for tool in bot_tools}
RETRIEVAL_TOOLS = {"search_menu", "search_info", "get_weather_forecast"}

# 2. Instancia del modelo Ollama en Docker con herramientas vinculadas
llm = ChatOllama(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL,
    temperature=0.1
)
llm_with_tools = llm.bind_tools(bot_tools)

# 3. Almacenamiento de sesiones en memoria
session_store: Dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in session_store:
        session_store[session_id] = ChatMessageHistory()
    return session_store[session_id]

# 4. Prompt del Sistema
SYSTEM_PROMPT = SystemMessage(
    content=(
        "Eres el asistente virtual oficial del restaurante RAGtaurant. Tu objetivo es ser servicial, preciso y amable. "
        "Responde siempre en español y atiende únicamente consultas sobre el restaurante, su información, su carta y reservas. "
        "Declina brevemente cualquier petición ajena a esos temas; no intentes resolverla.\n\n"
        "Usa `search_menu` para consultar la carta y `search_info` para consultar información institucional. "
        "Usa los datos recuperados como única fuente de verdad. Si no hay evidencia suficiente o la consulta no tiene resultados, "
        "indícalo claramente y no completes la respuesta con suposiciones. Para filtros dietéticos o de alergias, "
        "usa `vegan_only`, `vegetarian_only` y `exclude_allergens` de `search_menu`; nunca infieras esos atributos "
        "a partir de la descripción. Para recomendaciones, deja `available_only` activado; para comprobar si un plato "
        "concreto está disponible, desactívalo y comunica el estado registrado. No afirmes que un plato es seguro para "
        "una alergia: la contaminación cruzada no consta.\n\n"
        "Usa `get_weather_forecast` para responder sobre el tiempo en la ubicación configurada del restaurante. "
        "Para una fecha explícita, pasa la fecha en formato YYYY-MM-DD; no inventes ni extrapoles previsiones. "
        "Si el cliente pregunta por el día de una reserva, solo omite la fecha cuando esa reserva haya sido verificada "
        "en esta conversación con su código, email y teléfono; el sistema aplicará la fecha verificada. "
        "La previsión solo cubre hoy y los 13 días siguientes. Si la fecha no está disponible o falla el proveedor, "
        "comunica que no hay previsión sin inventar valores.\n\n"
        "Las herramientas de reserva disponibles son:\n"
        "1. `make_table_reservation`: Para validar y preparar una reserva (nombre, email, teléfono, fecha YYYY-MM-DD, hora HH:MM y comensales); no la registra.\n"
        "2. `get_table_reservation`: Para consultar una reserva usando su código, email y teléfono coincidentes.\n"
        "3. `edit_table_reservation`: Para preparar cambios de fecha, hora o comensales de una reserva "
        "usando su código, email y teléfono coincidentes; no la modifica hasta confirmación.\n"
        "4. `delete_table_reservation`: Para preparar la cancelación verificando código de reserva, email y teléfono.\n\n"
        "Antes de crear, modificar o cancelar, presenta un resumen y espera una confirmación afirmativa explícita en un mensaje posterior. "
        "Nunca consideres la llamada a la herramienta ni una confirmación anterior como consentimiento. "
        "Para crear, recoge todos los datos requeridos; no afirmes que la reserva se ha registrado hasta que el sistema lo confirme. "
        "Para consultar, modificar o cancelar una reserva, exige siempre su código, email y teléfono coincidentes. "
        "Para modificar, solo puedes cambiar fecha, hora y número de comensales."
    )
)

class RAGChatbotRunner:
    """Ejecutor del ciclo de pensamiento y herramientas (Tool Calling Loop) mediante LCEL."""

    def __init__(self) -> None:
        self.pending_creations: Dict[str, dict[str, str | int]] = {}
        self.pending_cancellations: Dict[str, dict[str, str]] = {}
        self.pending_updates: Dict[str, dict[str, object]] = {}
        self.verified_reservations: Dict[str, tuple[str, str]] = {}

    async def ainvoke(self, input_data: dict, config: dict) -> dict:
        session_id = config.get("configurable", {}).get("session_id")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("A non-empty session_id is required.")
        session_id = session_id.strip()
        history = get_session_history(session_id)
        user_text = input_data["input"]
        history.add_user_message(user_text)

        pending = self.pending_cancellations.get(session_id)
        if pending is not None:
            answer = self._confirmation_answer(user_text)
            if answer == "yes":
                contact = ReservationContact(email=pending["email"], phone=pending["phone"])
                try:
                    await reservation_service.cancel_reservation(pending["reservation_id"], contact)
                except ReservationNotFoundException:
                    self.pending_cancellations.pop(session_id)
                    output = self._reservation_not_found_message()
                except DatabaseException:
                    logger.exception("Failed to cancel a confirmed reservation")
                    output = (
                        "No se pudo completar la cancelación. Responde «sí» para volver "
                        "a intentarlo o «no» para descartar la solicitud."
                    )
                except Exception:
                    logger.exception("Unexpected failure canceling a confirmed reservation")
                    output = (
                        "No se pudo completar la cancelación. Responde «sí» para volver "
                        "a intentarlo o «no» para descartar la solicitud."
                    )
                else:
                    self.pending_cancellations.pop(session_id)
                    verified = self.verified_reservations.get(session_id)
                    if verified is not None and verified[0] == pending["reservation_id"]:
                        self.verified_reservations.pop(session_id)
                    output = f"La reserva '{pending['reservation_id']}' ha sido cancelada."
            elif answer == "no":
                self.pending_cancellations.pop(session_id)
                output = "De acuerdo, no se ha cancelado la reserva."
            else:
                output = "La cancelación sigue pendiente. Responde «sí» para confirmar o «no» para cancelar la solicitud."
            history.add_ai_message(output)
            return {"output": output}

        pending_creation = self.pending_creations.get(session_id)
        if pending_creation is not None:
            answer = self._confirmation_answer(user_text)
            if answer == "yes":
                self.pending_creations.pop(session_id)
                try:
                    reservation = ReservationCreate(**pending_creation)
                    created = await reservation_service.create_reservation(reservation)
                    output = (
                        f"La reserva se ha creado correctamente. Código: {created.reservation_id}."
                    )
                except ValidationError as exc:
                    output = self._reservation_validation_error(exc)
                except ReservationConflictException:
                    output = (
                        "No se ha creado la reserva: ya existe una reserva activa para esos "
                        "datos de contacto en esa fecha."
                    )
                except DatabaseException:
                    logger.exception("Failed to create a confirmed reservation")
                    output = (
                        "No se pudo registrar la reserva por un fallo del servicio. "
                        "No está confirmada; inténtalo de nuevo más tarde."
                    )
                except Exception:
                    logger.exception("Unexpected failure creating a confirmed reservation")
                    output = (
                        "No se pudo registrar la reserva por un fallo del servicio. "
                        "No está confirmada; inténtalo de nuevo más tarde."
                    )
            elif answer == "no":
                self.pending_creations.pop(session_id)
                output = (
                    "De acuerdo, no se ha creado la reserva. Puedes enviar los datos corregidos "
                    "para preparar una nueva solicitud."
                )
            else:
                output = (
                    "No se ha creado la reserva; la solicitud sigue pendiente. Responde «sí» "
                    "para confirmarla o «no» para descartarla. Para corregir algún dato, "
                    "responde «no» y vuelve a enviar los datos correctos."
                )
            history.add_ai_message(output)
            return {"output": output}

        pending_update = self.pending_updates.get(session_id)
        if pending_update is not None:
            answer = self._confirmation_answer(user_text)
            if answer == "yes":
                self.pending_updates.pop(session_id)
                try:
                    contact = ReservationContact(
                        email=pending_update["email"],
                        phone=pending_update["phone"],
                    )
                    update = ReservationUpdate(**pending_update["update"])
                    updated = await reservation_service.update_reservation(
                        pending_update["reservation_id"],
                        update,
                        contact,
                    )
                    self.verified_reservations.pop(session_id, None)
                    output = (
                        f"La reserva '{updated.reservation_id}' se ha modificado correctamente. "
                        f"Fecha: {updated.date.isoformat()}, hora: "
                        f"{updated.time.isoformat(timespec='minutes')}, comensales: "
                        f"{updated.guests}."
                    )
                except ValidationError as exc:
                    output = self._reservation_update_validation_error(exc)
                except ReservationConflictException:
                    output = (
                        "No se ha modificado la reserva: ya existe una reserva activa para esos "
                        "datos de contacto en esa fecha."
                    )
                except ReservationValidationException:
                    output = (
                        "No se ha modificado la reserva. Comprueba que siga activa y que la fecha "
                        "y la hora estén dentro del horario disponible."
                    )
                except DatabaseException:
                    logger.exception("Failed to update a confirmed reservation")
                    output = (
                        "No se pudo modificar la reserva por un fallo del servicio. "
                        "No se ha confirmado ningún cambio; inténtalo de nuevo más tarde."
                    )
                except Exception:
                    logger.exception("Unexpected failure updating a confirmed reservation")
                    output = (
                        "No se pudo modificar la reserva por un fallo del servicio. "
                        "No se ha confirmado ningún cambio; inténtalo de nuevo más tarde."
                    )
            elif answer == "no":
                self.pending_updates.pop(session_id)
                output = "De acuerdo, no se ha modificado la reserva."
            else:
                output = (
                    "La solicitud de cambio sigue pendiente. Responde «sí» para confirmar "
                    "o «no» para descartarla."
                )
            history.add_ai_message(output)
            return {"output": output}
        
        messages = [SYSTEM_PROMPT] + history.messages
        response = await llm_with_tools.ainvoke(messages)

        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls and all(call["name"] in RETRIEVAL_TOOLS for call in tool_calls):
            evidence = []
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                selected_tool = TOOLS_MAP.get(tool_name)
                if selected_tool is None:
                    evidence.append("No se pudo consultar la fuente autorizada.")
                    continue
                try:
                    result = await self._invoke_tool(tool_name, tool_call["args"], session_id)
                    evidence.append(str(result))
                except Exception:
                    logger.exception("Failed to retrieve chatbot evidence with %s", tool_name)
                    evidence.append("No pude consultar la información del restaurante en este momento.")
            final_output = "\n\n".join(evidence)
            history.add_ai_message(final_output)
            return {"output": final_output}

        max_iterations = 5
        iteration = 0
        reservation_lookup_output: str | None = None
        additional_tool_used = False
        
        while getattr(response, "tool_calls", None) and iteration < max_iterations:
            iteration += 1
            messages.append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call.get("id", tool_name)

                if tool_name == "make_table_reservation":
                    try:
                        reservation = prepare_table_reservation(tool_args)
                    except ValidationError as exc:
                        output = self._reservation_validation_error(exc)
                        history.add_ai_message(output)
                        return {"output": output}

                    self.pending_creations[session_id] = reservation.model_dump(mode="json")
                    output = format_reservation_confirmation(reservation)
                    history.add_ai_message(output)
                    return {"output": output}

                if tool_name == "edit_table_reservation":
                    try:
                        reservation, update = await prepare_table_reservation_update(**tool_args)
                    except ReservationNotFoundException:
                        output = self._reservation_not_found_message()
                    except ValidationError as exc:
                        output = self._reservation_update_validation_error(exc)
                    except TypeError:
                        output = self._reservation_not_found_message()
                    except ReservationValidationException:
                        output = (
                            "No se puede modificar esa reserva. Comprueba que siga activa y que "
                            "hayas indicado fecha, hora o comensales dentro de las reglas."
                        )
                    except DatabaseException:
                        logger.exception("Failed to prepare a reservation update")
                        output = "No se pudo consultar la reserva en este momento. Inténtalo más tarde."
                    else:
                        self.pending_updates[session_id] = {
                            "reservation_id": reservation.reservation_id,
                            "email": reservation.email,
                            "phone": reservation.phone,
                            "update": update.model_dump(mode="json", exclude_unset=True),
                        }
                        output = format_table_reservation_update(reservation, update)
                    history.add_ai_message(output)
                    return {"output": output}
                
                if tool_name in TOOLS_MAP:
                    if tool_name == "get_table_reservation":
                        reservation_lookup_output = self._reservation_not_found_message()
                    else:
                        additional_tool_used = True
                    try:
                        tool_output = await self._invoke_tool(tool_name, tool_args, session_id)
                        if tool_name == "get_table_reservation":
                            reservation_lookup_output = str(tool_output)
                        if tool_name == "delete_table_reservation":
                            self.pending_cancellations[session_id] = dict(tool_args)
                    except (ReservationNotFoundException, ValidationError, TypeError):
                        tool_output = self._reservation_not_found_message()
                        if tool_name == "get_table_reservation":
                            reservation_lookup_output = tool_output
                    except DatabaseException:
                        logger.exception("Failed to retrieve a chatbot reservation")
                        tool_output = "No se pudo consultar la reserva en este momento. Inténtalo más tarde."
                        if tool_name == "get_table_reservation":
                            reservation_lookup_output = tool_output
                    except Exception as e:
                        if tool_name == "delete_table_reservation":
                            self.pending_cancellations.pop(session_id, None)
                        if tool_name == "get_table_reservation":
                            tool_output = self._reservation_not_found_message()
                            reservation_lookup_output = tool_output
                        else:
                            tool_output = f"Error al ejecutar la herramienta {tool_name}: {str(e)}"
                else:
                    tool_output = f"Herramienta '{tool_name}' no encontrada."
                
                messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))
            
            response = await llm_with_tools.ainvoke(messages)
        
        if reservation_lookup_output is not None and not additional_tool_used:
            final_output = reservation_lookup_output
        else:
            final_output = response.content if isinstance(response.content, str) else str(response.content)
        history.add_ai_message(final_output)
        
        return {"output": final_output}

    async def _invoke_tool(
        self,
        tool_name: str,
        tool_args: dict,
        session_id: str,
    ) -> str:
        arguments = dict(tool_args)
        if tool_name == "search_menu":
            arguments = self._normalize_search_menu_arguments(arguments)
        if tool_name == "get_table_reservation":
            self.verified_reservations.pop(session_id, None)
            reservation = await get_verified_table_reservation(**arguments)
            if reservation.status == "confirmed":
                self.verified_reservations[session_id] = (
                    reservation.reservation_id,
                    reservation.date.isoformat(),
                )
            return format_verified_table_reservation(reservation)
        if tool_name == "edit_table_reservation":
            self.verified_reservations.pop(session_id, None)
        if tool_name == "get_weather_forecast" and arguments.get("date") is None:
            verified = self.verified_reservations.get(session_id)
            if verified is not None:
                arguments["date"] = verified[1]

        selected_tool = TOOLS_MAP.get(tool_name)
        if selected_tool is None:
            raise ValueError(f"Tool '{tool_name}' is not available.")
        return await selected_tool.ainvoke(arguments)

    @staticmethod
    def _normalize_search_menu_arguments(arguments: dict) -> dict:
        """Coerce loosely typed model output into the shape `search_menu` validates."""
        normalized = {key: value for key, value in arguments.items() if value is not None}
        allergens = normalized.get("exclude_allergens")
        if isinstance(allergens, str):
            allergens = [part.strip() for part in allergens.split(",")]
        if isinstance(allergens, list):
            normalized["exclude_allergens"] = [
                str(item).strip().casefold() for item in allergens if str(item).strip()
            ]
        for flag in ("vegan_only", "vegetarian_only", "available_only"):
            value = normalized.get(flag)
            if isinstance(value, str):
                normalized[flag] = value.strip().casefold() in {"true", "1", "yes", "sí", "si"}
        if not isinstance(normalized.get("query"), str):
            normalized["query"] = str(normalized.get("query") or "")
        return normalized

    @staticmethod
    def _confirmation_answer(message: str) -> str | None:
        normalized = unicodedata.normalize("NFKD", message.casefold())
        normalized = "".join(character for character in normalized if not unicodedata.combining(character))
        normalized = "".join(character if character.isalnum() else " " for character in normalized)
        normalized = " ".join(normalized.split())
        if normalized in {"si", "si confirmar", "confirmo", "confirmar", "adelante"}:
            return "yes"
        if normalized in {"no", "no cancelar", "no gracias", "cancelo"}:
            return "no"
        return None

    @staticmethod
    def _reservation_validation_error(error: ValidationError) -> str:
        field_names = {
            "customer_name": "nombre",
            "email": "email",
            "phone": "teléfono",
            "date": "fecha",
            "time": "hora",
            "guests": "número de comensales",
        }
        messages = []
        for item in error.errors():
            field = str(item["loc"][0]) if item["loc"] else "datos"
            label = field_names.get(field, "datos")
            detail = item["msg"].lower()
            if "field required" in detail:
                message = f"falta el {label}"
            elif "next 14 days" in detail:
                message = "la fecha debe estar entre hoy y los próximos 13 días"
            elif "time that has passed" in detail:
                message = "la hora indicada ya ha pasado"
            elif "available from 12:00 to 23:00" in detail:
                message = "el horario disponible es de 12:00 a 23:00"
            elif "available on the half-hour" in detail:
                message = "la hora debe estar en punto o en la media hora"
            elif field == "email":
                message = "el email no es válido"
            elif field == "phone":
                message = "el teléfono no es válido"
            elif field == "guests":
                message = "el número de comensales debe estar entre 1 y 20"
            else:
                message = f"revisa el campo {label}"
            messages.append(message)
        details = "; ".join(dict.fromkeys(messages))
        return f"No he creado ninguna reserva. Revisa los datos: {details}."

    @classmethod
    def _reservation_update_validation_error(cls, error: ValidationError) -> str:
        message = cls._reservation_validation_error(error)
        return message.replace("No he creado ninguna reserva.", "No se ha modificado la reserva.", 1)

    @staticmethod
    def _reservation_not_found_message() -> str:
        return (
            "No se encontró una reserva autorizada con esos datos. Comprueba el código "
            "de reserva, el email y el teléfono."
        )

# Exportamos el runner para app/api/chat.py
rag_chatbot = RAGChatbotRunner()