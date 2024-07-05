from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete, update, func
from typing import List

from app.api.endpoints.rate.models import Rate
from app.api.endpoints.receptionist.schemas import ReceptionistCreate, ReceptionistRead, ReceptionistInformation
from app.db.base import get_async_session
from app.api.endpoints.receptionist.models import Receptionist
from app.api.endpoints.ticket.models import Ticket

router = APIRouter(
    prefix="/receptionist",
    tags=["receptionist"]
)

@router.get("/all", response_model=List[ReceptionistInformation])
async def get_all_receptionists(session: AsyncSession = Depends(get_async_session)) -> List[ReceptionistInformation]:
    stmt = select(Receptionist).order_by(Receptionist.id)
    result = await session.execute(stmt)
    receptionists = result.scalars().all()

    all_receptionists = []

    for receptionist in receptionists:
        queue_stmt = select(func.count(Ticket.id)).where(Ticket.receptionist_id == receptionist.id, Ticket.status == "В очереди")
        queue_result = await session.execute(queue_stmt)
        queue_count = queue_result.scalar()

        avg_rate_stmt = select(func.avg(Rate.rate)).where(Rate.receptionist_id == receptionist.id)
        avg_rate_result = await session.execute(avg_rate_stmt)
        average_rate = avg_rate_result.scalar() or 0

        receptionist_info = ReceptionistInformation(
            id=receptionist.id,
            first_name=receptionist.first_name,
            last_name=receptionist.last_name,
            table_num=receptionist.table_num,
            photo=receptionist.photo,
            queue=queue_count,
            average_rate=average_rate
        )
        all_receptionists.append(receptionist_info)

    return all_receptionists

@router.get("/{receptionist_id}", response_model=ReceptionistRead)
async def get_receptionist_by_id(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:
    stmt = select(Receptionist).where(Receptionist.id == receptionist_id)
    result = await session.execute(stmt)
    receptionist = result.scalar_one_or_none()
    if not receptionist:
        raise HTTPException(status_code=404, detail="Receptionist not found")
    return receptionist

@router.post("/create", response_model=ReceptionistRead)
async def create_receptionist(new_receptionist: ReceptionistCreate, session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:
    stmt = select(Receptionist).where(Receptionist.email == new_receptionist.email)
    result = await session.execute(stmt)
    receptionist = result.scalar_one_or_none()
    if receptionist:
        raise HTTPException(status_code=400, detail="This email already exists")

    stmt = insert(Receptionist).values(**new_receptionist.dict()).returning(Receptionist.id)

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
    stmt = update(Receptionist).where(Receptionist.id == receptionist_id).values(**new_receptionist.dict()).returning(Receptionist.id)

    try:
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Receptionist not found")

        await session.commit()

        current_receptionist_stmt = select(Receptionist).where(Receptionist.id == receptionist_id)
        result = await session.execute(current_receptionist_stmt)
        updated_receptionist = result.scalar_one()
        return updated_receptionist
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))