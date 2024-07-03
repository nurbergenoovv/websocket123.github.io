from fastapi import FastAPI
import sys

from fastapi.middleware.cors import CORSMiddleware

sys.path.append('../')

from auth.base_config import auth_backend, fastapi_users
from auth.schemas import UserRead, UserCreate
from api.endpoints.websocket.router import router as ws_router

app = FastAPI(
    title='Sample API',
)
#
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(ws_router)

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