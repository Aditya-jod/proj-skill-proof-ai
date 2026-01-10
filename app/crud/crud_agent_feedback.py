from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.agent_feedback import AgentFeedback as AgentFeedbackModel
from ..schemas.feedback import AgentFeedbackCreate


def create_feedback(db: Session, payload: AgentFeedbackCreate) -> AgentFeedbackModel:
    record = AgentFeedbackModel(**payload.dict())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
