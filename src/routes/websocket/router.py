import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        print(f"WebSocket connected: {websocket}")
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"WebSocket disconnected: {websocket}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting message: {str(e)}")


manager = ConnectionManager()

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received message: {data}")
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket connection closed")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
