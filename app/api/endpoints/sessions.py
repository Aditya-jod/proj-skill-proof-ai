from fastapi import APIRouter
from pydantic import BaseModel

from ...services.session_manager import session_manager


router = APIRouter()


class SessionRequest(BaseModel):
    user_id: str
    mode: str = "learning"
    difficulty: str = "easy"
    topic: str = "recursion"


@router.post("/sessions")
def create_session(request: SessionRequest):
    bundle = session_manager.start_session(request.user_id, request.model_dump())
    state = bundle["state"]
    return {
        "user_id": state.user_id,
        "session_id": state.session_id,
        "mode": state.mode,
        "difficulty": state.difficulty,
        "topic": state.topic,
        "status": state.status,
    }
