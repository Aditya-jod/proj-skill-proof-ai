from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SkillProfileBase(BaseModel):
    debugging: float = Field(ge=0.0, le=1.0)
    logic: float = Field(ge=0.0, le=1.0)
    syntax: float = Field(ge=0.0, le=1.0)
    problem_decomposition: float = Field(ge=0.0, le=1.0)
    integrity_confidence: float = Field(ge=0.0, le=1.0)
    attempts: int = Field(ge=0)


class SkillProfileCreate(SkillProfileBase):
    user_id: str


class SkillProfileUpdate(SkillProfileBase):
    pass


class SkillProfile(SkillProfileBase):
    user_id: str
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
