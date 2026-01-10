from sqlalchemy.orm import Session
# from .. import models, schemas

def get_session(db: Session, session_id: int):
    # return db.query(models.Session).filter(models.Session.id == session_id).first()
    pass

def create_session(db: Session): #, session: schemas.SessionCreate
    # db_session = models.Session(**session.dict())
    # db.add(db_session)
    # db.commit()
    # db.refresh(db_session)
    # return db_session
    pass
