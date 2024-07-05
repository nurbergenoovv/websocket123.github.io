from unicodedata import decimal

from pydantic import BaseModel

class RateRead(BaseModel):
    id: int
    rate: int
    receptionist_id: int
    class Config:
        orm_mode = True

class RateCreate(BaseModel):
    rate: int
    receptionist_id: int

class RateAverage(BaseModel):
    average_rate: float
    receptionist_id: int