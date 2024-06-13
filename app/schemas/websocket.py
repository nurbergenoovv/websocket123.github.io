from pydantic import BaseModel, schema


class WebSocketBase(BaseModel):
    device_id: int
    status: int
    message: str

    class Config:
        orm_mode = True