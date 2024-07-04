from pydantic import BaseModel
from datetime import datetime
from pydantic import BaseModel

class TicketRead(BaseModel):
    id: int
    email: str
    status: str
    receptionist_id: int
    date_time: datetime  # Adjust this according to how you want to handle timestamps
    class Config:
        orm_mode = True

class TicketCreate(BaseModel):
    email: str
    receptionist_id: int
