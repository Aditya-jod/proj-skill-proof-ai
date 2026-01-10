from pydantic import BaseModel
import datetime

class SessionBase(BaseModel):
    user_id: str
    mode: str

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    id: int
    start_time: datetime.datetime

    class Config:
        orm_mode = True
