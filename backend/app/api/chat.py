# app/api/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.rag.agent import rag_chatbot

router = APIRouter(prefix="/chat", tags=["Chatbot RAG"])

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"

class ChatResponse(BaseModel):
    response: str
    session_id: str

@router.post("/", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    
    try:
        config = {"configurable": {"session_id": payload.session_id}}
        result = rag_chatbot.invoke({"input": payload.message}, config=config)
        return ChatResponse(
            response=result["output"],
            session_id=payload.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando la solicitud: {str(e)}")