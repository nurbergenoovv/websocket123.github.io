from fastapi import FastAPI
import sys

from fastapi.middleware.cors import CORSMiddleware

sys.path.append('../')

from app.api.endpoints.receptionist.router import router as receptionist_router
from app.api.endpoints.websocket.router import router as ws_router
from app.api.endpoints.ticket.router import router as ticket_router
from app.api.endpoints.rate.router import router as rate_router

app = FastAPI(
    title='Sample API',
)

app.include_router(ws_router)
app.include_router(receptionist_router)
app.include_router(ticket_router)
app.include_router(rate_router)
@app.get("/")
def read_root():
    return {f"Hello"}


origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                   "Authorization"],
)