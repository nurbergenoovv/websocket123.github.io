from pydantic import BaseModel


class TicketModel(BaseModel):
    id: int
    email: str
    status: str
    worker_id: int

    class Config:
        orm_mode = True

class TicketCreate(BaseModel):
    email: str
    worker_id: int


