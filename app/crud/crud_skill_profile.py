from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.skill_profile import SkillProfile as SkillProfileModel
from ..schemas.skill_profile import SkillProfileCreate, SkillProfileUpdate


def get_profile(db: Session, user_id: str) -> SkillProfileModel | None:
    return db.query(SkillProfileModel).filter(SkillProfileModel.user_id == user_id).first()


def create_profile(db: Session, payload: SkillProfileCreate) -> SkillProfileModel:
    record = SkillProfileModel(**payload.dict())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_profile(db: Session, user_id: str, payload: SkillProfileUpdate) -> SkillProfileModel:
    record = get_profile(db, user_id)
    if record is None:
        return create_profile(db, SkillProfileCreate(user_id=user_id, **payload.dict()))
    for field, value in payload.dict().items():
        setattr(record, field, value)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
