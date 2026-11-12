import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints

from app.core.config import settings
from app.core.rate_limit import enforce_chat_rate_limit
from app.rag.agent import rag_chatbot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chatbot RAG"])

SessionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(max_length=settings.CHAT_MAX_MESSAGE_CHARS)]
    session_id: SessionId


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/", response_model=ChatResponse, dependencies=[Depends(enforce_chat_rate_limit)])
async def chat_endpoint(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        config = {"configurable": {"session_id": payload.session_id}}
        result = await rag_chatbot.ainvoke({"input": payload.message}, config=config)
        return ChatResponse(response=result["output"], session_id=payload.session_id)
    except Exception:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail="Error processing the request.") from None
