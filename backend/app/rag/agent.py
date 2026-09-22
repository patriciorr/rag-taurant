# app/rag/agent.py
from typing import Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from app.core.config import settings
from app.rag.tools import bot_tools

# 1. Mapa de herramientas por nombre para invocación directa
TOOLS_MAP = {tool.name: tool for tool in bot_tools}

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
        "Responde siempre en español.\n\n"
        "Cuentas con las siguientes herramientas especializadas que DEBES usar antes de responder:\n"
        "1. `search_menu`: Para consultar la carta, ingredientes, alérgenos, ofertas veganas/vegetarianas y precios de platos.\n"
        "2. `search_info`: Para consultar dudas sobre ubicación, horarios, parking, terraza o políticas del restaurante.\n"
        "3. `get_weather_forecast`: Para consultar la previsión meteorológica.\n"
        "4. `make_table_reservation`: Para registrar nuevas reservas (requiere nombre, email, teléfono, fecha YYYY-MM-DD, hora HH:MM y número de comensales).\n"
        "5. `get_table_reservation`: Para buscar y mostrar una reserva usando el ID, email o teléfono del cliente.\n"
        "6. `edit_table_reservation`: Para modificar fecha, hora, comensales o nombre de una reserva existente usando su ID, email o teléfono.\n"
        "7. `delete_table_reservation`: Para cancelar/eliminar una reserva mediante su ID, email o teléfono.\n\n"
        "Si el usuario intenta modificar o cancelar una reserva pero no proporciona su ID, email o teléfono, pídeselo amablemente antes de llamar a la herramienta."
    )
)

class RAGChatbotRunner:
    """Ejecutor del ciclo de pensamiento y herramientas (Tool Calling Loop) mediante LCEL."""

    def invoke(self, input_data: dict, config: dict) -> dict:
        session_id = config.get("configurable", {}).get("session_id", "default")
        history = get_session_history(session_id)
        user_text = input_data["input"]
        
        # Registrar entrada del usuario
        history.add_user_message(user_text)
        
        # Preparar historial de mensajes para el modelo
        messages = [SYSTEM_PROMPT] + history.messages
        
        # Primera invocación
        response = llm_with_tools.invoke(messages)
        
        # Bucle de ejecución de herramientas si el modelo decide llamar a alguna
        max_iterations = 5
        iteration = 0
        
        while getattr(response, "tool_calls", None) and iteration < max_iterations:
            iteration += 1
            messages.append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call.get("id", tool_name)
                
                selected_tool = TOOLS_MAP.get(tool_name)
                if selected_tool:
                    try:
                        tool_output = selected_tool.invoke(tool_args)
                    except Exception as e:
                        tool_output = f"Error al ejecutar la herramienta {tool_name}: {str(e)}"
                else:
                    tool_output = f"Herramienta '{tool_name}' no encontrada."
                
                messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_id))
            
            # Segunda invocación tras inyectar la salida de las herramientas
            response = llm_with_tools.invoke(messages)
        
        final_output = response.content if isinstance(response.content, str) else str(response.content)
        history.add_ai_message(final_output)
        
        return {"output": final_output}

# Exportamos el runner con la interfaz .invoke() esperada por app/api/chat.py
rag_chatbot = RAGChatbotRunner()