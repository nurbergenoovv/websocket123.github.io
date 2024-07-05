from pydantic import BaseModel

class ReceptionistRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    photo: str

    class Config:
        orm_mode = True

class ReceptionistCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    photo: str
    table_num: int

class ReceptionistInformation(BaseModel):
    id: int
    first_name: str
    last_name: str
    table_num: int
    photo: str
    average_rate: float
    queue: int