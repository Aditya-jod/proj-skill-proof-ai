from sqlalchemy.orm import Session

from .. import models, schemas


def get_session(db: Session, session_id: int) -> models.Session | None:
    """Fetch a stored session row by primary key."""
    return db.query(models.Session).filter(models.Session.id == session_id).first()


def create_session(db: Session, session: schemas.SessionCreate) -> models.Session:
    """Persist a new session record using the SQLite-backed engine."""
    db_session = models.Session(**session.dict())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session
