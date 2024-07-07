from typing import Optional

from fastapi import Depends, Request, HTTPException
from fastapi_users import BaseUserManager, IntegerIDMixin, exceptions, models, schemas
from sqlalchemy import select
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.utils import get_user_db

from src.config import SECRET_AUTH
from src.database import async_session_maker, get_async_session


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET_AUTH
    verification_token_secret = SECRET_AUTH

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
            self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def create(
            self,
            user_create: schemas.UC,
            safe: bool = False,
            request: Optional[Request] = None,
    ) -> models.UP:
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user


async def delete(
        user_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> dict:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    stmt1 = sqlalchemy_delete(User).where(User.id == user_id)
    await session.execute(stmt1)
    await session.commit()  # Фиксируем изменения в базе данных
    print(f"User id {user_id} has been deleted.")

    return {"detail": "User deleted successfully"}

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
