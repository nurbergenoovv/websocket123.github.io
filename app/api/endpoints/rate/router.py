from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete

from app.api.endpoints.rate.schemas import RateRead, RateCreate, RateAverage
from app.api.endpoints.rate.models import Rate
from app.db.base import get_async_session
from app.schemas.schemas import ReturnMessage

router = APIRouter(
    prefix="/rate",
    tags=["rate"]
)

@router.get('/{receptionist_id}', response_model=List[RateRead])
async def get_rates_by_receptionist_id(
    receptionist_id: int,
    session: AsyncSession = Depends(get_async_session)
) -> List[RateRead]:
    stmt = select(Rate).where(Rate.receptionist_id == receptionist_id)
    result = await session.execute(stmt)
    rates = result.scalars().all()

    return rates

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

@router.get('/{receptionist_id}/average', response_model=RateAverage)
async def get_average_rate_by_receptionist_id(
    receptionist_id: int,
    session: AsyncSession = Depends(get_async_session)
) -> RateAverage:
    stmt = select(func.avg(Rate.rate)).where(Rate.receptionist_id == receptionist_id)
    result = await session.execute(stmt)
    average_rate = result.scalar()

    if average_rate is None:
        return {
            "average_rate": 0,
            "receptionist_id": receptionist_id
        }

    return RateAverage(average_rate=average_rate, receptionist_id=receptionist_id)



@router.post('/add', response_model=RateRead)
async def add_rate_to_receptionist(
    new_rate: RateCreate,
    session: AsyncSession = Depends(get_async_session)
) -> RateRead:
    stmt = insert(Rate).values(
        receptionist_id=new_rate.receptionist_id,
        rate=new_rate.rate
    ).returning(Rate.id)
    result = await session.execute(stmt)
    await session.commit()
    return {
        "receptionist_id": new_rate.receptionist_id,
        "rate": new_rate.rate,
        "id": result.scalar_one(),
    }

@router.delete("/{rate_id}", response_model=ReturnMessage)
async def delete_rate_from_receptionist(rate_id: int, session: AsyncSession = Depends(get_async_session)) -> ReturnMessage:
    # Check if the rate exists
    stmt = select(Rate).where(Rate.id == rate_id)
    result = await session.execute(stmt)
    rate = result.scalar_one_or_none()

    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    # Delete the rate
    stmt = delete(Rate).where(Rate.id == rate_id)
    await session.execute(stmt)
    await session.commit()

    return ReturnMessage(message="Rate deleted", status="ok")