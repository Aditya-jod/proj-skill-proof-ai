from sqlalchemy.orm import Session

from ..models.session import Session as SessionModel
from ..schemas.session import SessionCreate


def get_session(db: Session, session_id: int) -> SessionModel | None:
    """Fetch a stored session row by primary key."""
    return db.query(SessionModel).filter(SessionModel.id == session_id).first()


def create_session(db: Session, session: SessionCreate) -> SessionModel:
    """Persist a new session record using the SQLite-backed engine."""
    db_session = SessionModel(**session.dict())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session
