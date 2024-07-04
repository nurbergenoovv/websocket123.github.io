from app.api.endpoints.receptionist.schemas import ReceptionistCreate, ReceptionistRead
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete, update
from app.db.base import get_async_session
from app.api.endpoints.receptionist.models import Receptionist
from typing import List

router = APIRouter(
    prefix="/receptionist",
    tags=["receptionist"]
)

@router.get("/all", response_model=List[ReceptionistRead])
async def get_all_receptionists(session: AsyncSession = Depends(get_async_session)) -> List[ReceptionistRead]:
    stmt = select(Receptionist).order_by(Receptionist.id)
    result = await session.execute(stmt)
    receptionists = result.scalars().all()
    return receptionists

@router.get("/{receptionist_id}", response_model=ReceptionistRead)
async def get_receptionist_by_id(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:
    stmt = select(Receptionist).where(Receptionist.id == receptionist_id)
    result = await session.execute(stmt)
    receptionist = result.scalar_one()
    return receptionist


@router.post("/create", response_model=ReceptionistRead)
async def create_receptionist(new_receptionist: ReceptionistCreate,
                              session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:
    stmt = insert(Receptionist).values(
        first_name=new_receptionist.first_name,
        last_name=new_receptionist.last_name,
        email=new_receptionist.email,
        photo=new_receptionist.photo,
        table_num=new_receptionist.table_num
    ).returning(Receptionist.id)

    try:
        result = await session.execute(stmt)
        receptionist_id = result.scalar_one()
        await session.commit()

        current_receptionist_stmt = select(Receptionist).where(Receptionist.id == receptionist_id)
        result = await session.execute(current_receptionist_stmt)
        current_receptionist = result.scalar_one()
        return current_receptionist
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{receptionist_id}")
async def delete_receptionist_by_id(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> dict:
    stmt = delete(Receptionist).where(Receptionist.id == receptionist_id)

    try:
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Receptionist not found")

        await session.commit()
        return {"message": "Receptionist deleted"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{receptionist_id}", response_model=ReceptionistRead)
async def update_receptionist_by_id(receptionist_id: int, new_receptionist: ReceptionistCreate, session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:
    stmt = update(Receptionist).where(Receptionist.id == receptionist_id).values(
        first_name=new_receptionist.first_name,
        last_name=new_receptionist.last_name,
        email=new_receptionist.email,
        photo=new_receptionist.photo,
        table_num=new_receptionist.table_num
    ).returning(Receptionist.id)

    try:
        result = await session.execute(stmt)
        receptionist_id = result.scalar_one()
        await session.commit()

        current_receptionist_stmt = select(Receptionist).where(Receptionist.id == receptionist_id)
        result = await session.execute(current_receptionist_stmt)
        updated_receptionist = result.scalar_one()
        return updated_receptionist
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))