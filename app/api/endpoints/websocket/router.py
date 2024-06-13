from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import Boolean

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)


class ConnectionManager:
    status: Boolean = False
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json({
            "status": self.status
        })
        print("Connected")
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        count: int = 0
        for connection in self.active_connections:
            if count == 0:
                print(message)
                if message == 'toggle':
                    if self.status:
                        self.status = False
                    else:
                        self.status = True
                    print(self.status)

                count+=1
            await connection.send_json({
                "status": self.status
            })


manager = ConnectionManager()


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await  manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Disconnected")
