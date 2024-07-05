import json
from typing import Any

from pydantic import BaseModel

class ReturnMessage(BaseModel):
    status: str
    message: str

class sendWS:
    def __init__(self, command, to, data):
        self.command: str = command
        self.to: int = to
        self.data: Any = data

    def to_json(self):
        message = {
            "command": self.command,
            "to": self.to,
            "data": self.data
        }
        return json.dumps(message)


class EmailInput(BaseModel):
    email: str
