
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.base_config import auth_backend, fastapi_users
from src.auth.manager import delete
from src.auth.models import User
from src.auth.schemas import UserRead, UserCreate
from src.database import async_session_maker, get_async_session


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate)
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)
router.include_router(
    fastapi_users.get_reset_password_router(),
)
router.include_router(fastapi_users.get_auth_router(auth_backend))
@router.delete('/{user_id}')
async def delete_user(user_id: int,
                      session: AsyncSession = Depends(get_async_session)):
    print("rate 0")
    return await delete(user_id, session)
@router.post('/check', response_model=UserRead)
async def get_info(user: User = Depends(fastapi_users.current_user())) -> UserRead:
    return user