from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.routes.Ticket.router import router as ticket_router
from src.routes.websocket.router import router as websocket_router
from src.routes.workers.router import router as worker_router

app = FastAPI(
    title="Queue APP"
)

origins = [
    "http://192.168.1.27",
    "http://192.168.1.27:3000",
    "http://localhost:3000",
    "*"# Add localhost for local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth router
app.include_router(auth_router)
app.include_router(ticket_router)
app.include_router(websocket_router)
app.include_router(worker_router)



