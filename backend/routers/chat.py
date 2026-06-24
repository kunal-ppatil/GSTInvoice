from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .auth import get_current_user
from .. import models, schemas
from ..gst_processor.chat_agent import BackendChatAgent

router = APIRouter(prefix="/chat", tags=["AI Assistant"])
chat_agent = BackendChatAgent()

@router.post("", response_model=schemas.ChatResponse)
def api_chat(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Processes natural language questions about invoices and returns structured data"""
    res = chat_agent.process_query(db, current_user.id, request.message)
    return schemas.ChatResponse(
        reply=res["reply"],
        suggested_actions=res.get("suggested_actions")
    )
