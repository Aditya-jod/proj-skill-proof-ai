from pydantic import BaseModel, ConfigDict
import datetime

class SessionBase(BaseModel):
    user_id: str
    mode: str

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    id: int
    start_time: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
