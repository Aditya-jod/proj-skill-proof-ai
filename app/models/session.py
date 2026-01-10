from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime

from ..db.base import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    mode = Column(String, default="learning") # learning or test
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
