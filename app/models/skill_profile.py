from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from ..db.base import Base


class SkillProfile(Base):
    __tablename__ = "skill_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, nullable=False, index=True)
    debugging = Column(Float, default=0.5)
    logic = Column(Float, default=0.5)
    syntax = Column(Float, default=0.5)
    problem_decomposition = Column(Float, default=0.5)
    integrity_confidence = Column(Float, default=0.5)
    attempts = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "debugging": self.debugging,
            "logic": self.logic,
            "syntax": self.syntax,
            "problem_decomposition": self.problem_decomposition,
            "integrity_confidence": self.integrity_confidence,
            "attempts": self.attempts,
        }
