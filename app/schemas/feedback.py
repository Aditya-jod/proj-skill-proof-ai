from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)
