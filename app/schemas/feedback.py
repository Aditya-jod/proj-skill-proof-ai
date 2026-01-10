from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class AgentFeedbackCreate(BaseModel):
    session_id: int
    agent: str
    note: str


class AgentFeedback(BaseModel):
    id: int
    session_id: int
    agent: str
    note: str
    created_at: datetime

    class Config:
        orm_mode = True
