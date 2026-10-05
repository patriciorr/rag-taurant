# app/rag/agent.py
import unicodedata
import logging
from typing import Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from app.core.config import settings
from app.models.reservation import ReservationContact
from app.rag.tools import (
    bot_tools,
    format_verified_table_reservation,
    get_verified_table_reservation,
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
        "1. `make_table_reservation`: Para registrar una reserva (nombre, email, teléfono, fecha YYYY-MM-DD, hora HH:MM y comensales).\n"
        "2. `get_table_reservation`: Para consultar una reserva usando su código, email y teléfono coincidentes.\n"
        "3. `edit_table_reservation`: Para modificar una reserva.\n"
        "4. `delete_table_reservation`: Para preparar la cancelación verificando código de reserva, email y teléfono.\n\n"
        "Antes de cancelar, presenta un resumen y espera una confirmación afirmativa explícita en un mensaje posterior. "
        "Nunca consideres la llamada a la herramienta ni una confirmación anterior como consentimiento. "
        "Para cancelar una reserva, exige su código, email y teléfono coincidentes."
    )
)

class RAGChatbotRunner:
    """Ejecutor del ciclo de pensamiento y herramientas (Tool Calling Loop) mediante LCEL."""

    def __init__(self) -> None:
        self.pending_cancellations: Dict[str, dict[str, str]] = {}
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
                await reservation_service.cancel_reservation(pending["reservation_id"], contact)
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
                    if tool_name == "get_table_reservation":
                        evidence.append("No pude verificar la reserva con esos datos.")
                    else:
                        evidence.append("No pude consultar la información del restaurante en este momento.")
            final_output = "\n\n".join(evidence)
            history.add_ai_message(final_output)
            return {"output": final_output}

        max_iterations = 5
        iteration = 0
        
        while getattr(response, "tool_calls", None) and iteration < max_iterations:
            iteration += 1
            messages.append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call.get("id", tool_name)
                
                if tool_name in TOOLS_MAP:
                    try:
                        tool_output = await self._invoke_tool(tool_name, tool_args, session_id)
                        if tool_name == "delete_table_reservation":
                            self.pending_cancellations[session_id] = dict(tool_args)
                    except Exception as e:
                        if tool_name == "delete_table_reservation":
                            self.pending_cancellations.pop(session_id, None)
                        if tool_name == "get_table_reservation":
                            tool_output = "No pude verificar la reserva con esos datos."
                        else:
                            tool_output = f"Error al ejecutar la herramienta {tool_name}: {str(e)}"
                else:
                    tool_output = f"Herramienta '{tool_name}' no encontrada."
                
                messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))
            
            response = await llm_with_tools.ainvoke(messages)
        
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

# Exportamos el runner para app/api/chat.py
rag_chatbot = RAGChatbotRunner()