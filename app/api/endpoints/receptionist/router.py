from app.api.endpoints.rate.models import Rate
from app.api.endpoints.rate.router import get_average_rate_by_receptionist_id
from app.api.endpoints.receptionist.schemas import ReceptionistCreate, ReceptionistRead, ReceptionistInformation
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete, update, func
from app.db.base import get_async_session
from app.api.endpoints.receptionist.models import Receptionist
from typing import List
from app.api.endpoints.websocket.router import ConnectionManager
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
        stmt = select(Ticket).where(Ticket.receptionist_id == receptionist.id, Ticket.status == "В очереди")
        result = await session.execute(stmt)

        stmt = select(func.avg(Rate.rate)).where(Rate.receptionist_id == receptionist.id)
        res = await session.execute(stmt)
        average_rate = res.scalar()

        if not average_rate:
            average_rate = 0

        reseption_information = ReceptionistInformation(
            id=receptionist.id,
            first_name=receptionist.first_name,
            last_name=receptionist.last_name,
            table_num = receptionist.table_num,
            photo=receptionist.photo,
            queue=len(result.scalars().all()),
            average_rate=average_rate
        )
        all_receptionists.append(reseption_information)

    return all_receptionists


@router.get("/{receptionist_id}", response_model=ReceptionistRead)
async def get_receptionist_by_id(receptionist_id: int,
                                 session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:
    stmt = select(Receptionist).where(Receptionist.id == receptionist_id)
    result = await session.execute(stmt)
    receptionist = result.scalar_one()
    return receptionist


@router.post("/create", response_model=ReceptionistRead)
async def create_receptionist(new_receptionist: ReceptionistCreate,
                              session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:

    stmt = select(Receptionist).where(Receptionist.email == new_receptionist.email)
    result = await session.execute(stmt)
    receptionist = result.scalar_one_or_none()
    if receptionist:
        raise HTTPException(status_code=400, detail="This email already exists")
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
async def update_receptionist_by_id(receptionist_id: int, new_receptionist: ReceptionistCreate,
                                    session: AsyncSession = Depends(get_async_session)) -> ReceptionistRead:
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
