from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...services.session_manager import session_manager
from ...services.auth_service import auth_service


router = APIRouter()


class SessionRequest(BaseModel):
    user_id: str | None = None
    mode: str = "learning"
    difficulty: str = "easy"
    topic: str = "recursion"


@router.post("/sessions")
def create_session(payload: SessionRequest, request: Request):
    user = auth_service.current_user(request)
    if not user or user.get("role") != "candidate":
        raise HTTPException(status_code=401, detail="Unauthorized")
    meta = payload.model_dump()
    bundle = session_manager.start_session(user["user_id"], meta)
    state = bundle["state"]
    return {
        "user_id": state.user_id,
        "session_id": state.session_id,
        "mode": state.mode,
        "difficulty": state.difficulty,
        "topic": state.topic,
        "status": state.status,
    }
