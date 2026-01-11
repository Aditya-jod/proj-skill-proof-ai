from typing import Optional

from sqlalchemy.orm import Session

from ..models.user_account import UserAccount


def get(db: Session, user_id: int) -> Optional[UserAccount]:
    return db.query(UserAccount).filter(UserAccount.id == user_id).first()


def get_by_email(db: Session, email: str) -> Optional[UserAccount]:
    return db.query(UserAccount).filter(UserAccount.email == email.lower()).first()


def create_user(db: Session, *, name: str, email: str, password_hash: str, role: str = "candidate") -> UserAccount:
    user = UserAccount(name=name, email=email.lower(), password_hash=password_hash, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
