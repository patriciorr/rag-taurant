# app/api/chat.py
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints

from app.rag.agent import rag_chatbot

router = APIRouter(prefix="/chat", tags=["Chatbot RAG"])

SessionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]

class ChatRequest(BaseModel):
    message: str
    session_id: SessionId

class ChatResponse(BaseModel):
    response: str
    session_id: str

@router.post("/", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    try:
        config = {"configurable": {"session_id": payload.session_id}}
        result = await rag_chatbot.ainvoke({"input": payload.message}, config=config)
        return ChatResponse(
            response=result["output"],
            session_id=payload.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the request: {str(e)}")