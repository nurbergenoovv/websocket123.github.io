from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete, update
from app.db.base import get_async_session
from app.api.endpoints.ticket.models import Ticket
from app.api.endpoints.ticket.schemas import TicketCreate, TicketRead
from typing import List

router = APIRouter(
    prefix="/ticket",
    tags=["ticket"]
)


@router.get("/all", response_model=List[TicketRead])
async def get_all_tickets(session: AsyncSession = Depends(get_async_session)) -> List[TicketRead]:
    try:
        stmt = select(Ticket).order_by(Ticket.id)
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        return tickets
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket_by_id(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    try:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one()
        return ticket
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticket with id {ticket_id} not found")


@router.get("/by_receptionist/{receptionist_id}", response_model=List[TicketRead])
async def get_tickets_by_receptionist_id(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> \
List[TicketRead]:
    try:
        stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id)
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        return tickets
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=TicketRead)
async def create_ticket(new_ticket: TicketCreate, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    try:
        stmt = insert(Ticket).values(
            email=new_ticket.email,
            receptionist_id=new_ticket.receptionist_id,
            status="В очереди"
        ).returning(Ticket.id)

        result = await session.execute(stmt)
        ticket_id = result.scalar_one()
        await session.commit()

        current_ticket_stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await session.execute(current_ticket_stmt)
        current_ticket = result.scalar_one()
        return current_ticket
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{ticket_id}")
async def delete_ticket_by_id(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> dict:
    try:
        stmt = delete(Ticket).where(Ticket.id == ticket_id)

        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ticket not found")

        await session.commit()
        return {"message": "Ticket deleted"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{ticket_id}", response_model=TicketRead)
async def update_ticket_by_id(ticket_id: int, new_ticket: TicketCreate,
                              session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    try:
        stmt = update(Ticket).where(Ticket.id == ticket_id).values(
            receptionist_id=new_ticket.receptionist_id,
        ).returning(Ticket.id)

        result = await session.execute(stmt)
        ticket_id = result.scalar_one()
        await session.commit()

        current_ticket_stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await session.execute(current_ticket_stmt)
        updated_ticket = result.scalar_one()
        return updated_ticket
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{receptionist_id}/start", response_model=TicketRead)
async def start_servicing(
        receptionist_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> TicketRead:
    try:
        # Find the earliest ticket in queue for the receptionist
        stmt = select(Ticket).where(
            Ticket.receptionist_id == receptionist_id,
            Ticket.status == "В очереди"
        ).order_by(Ticket.id)

        result = await session.execute(stmt)
        ticket = result.scalars().first()
        print(ticket)
        # Update its status to "В процессе"
        ticket.status = "В процессе"
        await session.commit()

        return ticket

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{receptionist_id}/next", response_model=TicketRead)
async def next_ticket(
        receptionist_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> TicketRead:
    try:
        # Find the ticket currently being serviced
        current_ticket_stmt = select(Ticket).where(
            Ticket.receptionist_id == receptionist_id,
            Ticket.status == "В процессе"
        )
        result = await session.execute(current_ticket_stmt)
        current_ticket = result.scalars().first()

        # Update its status to "Завершенный"
        current_ticket.status = "Завершенный"

        # Find the next ticket in queue for the receptionist
        next_ticket_stmt = select(Ticket).where(
            Ticket.receptionist_id == receptionist_id,
            Ticket.status == "В очереди"
        ).order_by(Ticket.id)

        result = await session.execute(next_ticket_stmt)
        next_ticket = result.scalars().first()

        # Update its status to "В процессе"
        next_ticket.status = "В процессе"
        await session.commit()

        return next_ticket

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{receptionist_id}/finish", response_model=TicketRead)
async def finish_ticket(
        receptionist_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> TicketRead:
    try:
        # Find the ticket currently being serviced
        stmt = select(Ticket).where(
            Ticket.receptionist_id == receptionist_id,
            Ticket.status == "В процессе"
        )

        result = await session.execute(stmt)
        ticket = result.scalars().first()

        # Update its status to "Завершенный"
        ticket.status = "Завершенный"
        await session.commit()

        return ticket

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ticket_id}/cancel", response_model=TicketRead)
async def cancel_ticket(
        ticket_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> TicketRead:
    try:
        # Query to find the ticket by ticket_id
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one()

        # Update the ticket's status to "Отменен"
        ticket.status = "Отменен"
        await session.commit()

        return ticket

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ticket_id}/pass", response_model=TicketRead)
async def pass_ticket(
        ticket_id: int,
        session: AsyncSession = Depends(get_async_session)
) -> TicketRead:
    try:
        # Query to find the ticket by ticket_id
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one()

        # Update the ticket's status to "Отменен"
        ticket.status = "Пропущено"
        await session.commit()

        return ticket

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
