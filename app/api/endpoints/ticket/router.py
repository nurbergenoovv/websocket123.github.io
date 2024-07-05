from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from typing import List

from app.db.base import get_async_session
from app.api.endpoints.ticket.models import Ticket
from app.api.endpoints.ticket.schemas import TicketCreate, TicketRead, TicketReadWS, TicketForPage
from app.schemas.schemas import sendWS, EmailInput, ReturnMessage
from app.api.endpoints.receptionist.models import Receptionist
from app.api.endpoints.websocket.router import manager

router = APIRouter(
    prefix="/ticket",
    tags=["ticket"]
)


@router.get("/all", response_model=List[TicketRead])
async def get_all_tickets(session: AsyncSession = Depends(get_async_session)) -> List[TicketRead]:
    stmt = select(Ticket).order_by(Ticket.id)
    result = await session.execute(stmt)
    tickets = result.scalars().all()
    return tickets


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket_by_id(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket with id {ticket_id} not found")
    return ticket


@router.get("/{ticket_id}/page", response_model=TicketForPage)
async def get_ticket_by_id_page(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketForPage:
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket with id {ticket_id} not found")

    readable_str = ticket.date_time.strftime("%Y-%m-%d %H:%M")
    return TicketForPage(
        id=ticket_id,
        date_time=readable_str,
        receptionist_id=ticket.receptionist_id,
        status=ticket.status,
    )


@router.post('/check_by_email', response_model=TicketRead)
async def get_by_email(email_input: EmailInput = Body(...), session: AsyncSession = Depends(get_async_session)):
    stmt = select(Ticket).where(Ticket.email == email_input.email)
    result = await session.execute(stmt)
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/by_receptionist/{receptionist_id}", response_model=List[TicketRead])
async def get_tickets_by_receptionist_id(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> \
List[TicketRead]:
    stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id, Ticket.status == "В очереди")
    result = await session.execute(stmt)
    tickets = result.scalars().all()
    return tickets


@router.get("/by_receptionist/{receptionist_id}/queue")
async def get_queue_length_by_receptionist_id(receptionist_id: int,
                                              session: AsyncSession = Depends(get_async_session)) -> int:
    stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id, Ticket.status == "В очереди")
    result = await session.execute(stmt)
    tickets = result.scalars().all()
    return len(tickets) - 1


@router.post("/create", response_model=TicketRead)
async def create_ticket(new_ticket: TicketCreate, response: Response,
                        session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    try:
        async with session.begin():
            ticket = Ticket(
                email=new_ticket.email,
                receptionist_id=new_ticket.receptionist_id,
                status="В очереди"
            )
            session.add(ticket)
            await session.flush()

            await session.commit()

            ticket_data = TicketRead(
                id=ticket.id,
                email=new_ticket.email,
                status=ticket.status,
                receptionist_id=new_ticket.receptionist_id,
                date_time=ticket.date_time
            )
            response.set_cookie(key="email", value=new_ticket.email, httponly=True, path='/', max_age=99900)

            await manager.broadcast(sendWS("new_ticket", ticket.receptionist_id, ticket_data.json()).to_json())

            return ticket_data
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete")
async def delete_ticket_by_email(request: Request, session: AsyncSession = Depends(get_async_session)) -> dict:
    data = await request.json()
    email = data.get("email")
    stmt = delete(Ticket).where(Ticket.email == email)

    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")

    await session.commit()
    return {"message": "Ticket deleted"}


@router.delete("/{ticket_id}")
async def delete_ticket_by_id(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> dict:
    stmt = delete(Ticket).where(Ticket.id == ticket_id)

    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")

    await session.commit()
    return {"message": "Ticket deleted"}


@router.delete("/by_receptionist/{receptionist_id}", response_model=ReturnMessage)
async def delete_tickets_by_receptionist_id(receptionist_id: int,
                                            session: AsyncSession = Depends(get_async_session)) -> ReturnMessage:
    stmt = delete(Ticket).where(Ticket.receptionist_id == receptionist_id)

    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="No tickets found for the receptionist")

    await session.commit()
    return {"message": "Tickets deleted"}


@router.put("/{ticket_id}", response_model=TicketRead)
async def update_ticket_by_id(ticket_id: int, new_ticket: TicketCreate,
                              session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    stmt = update(Ticket).where(Ticket.id == ticket_id).values(
        receptionist_id=new_ticket.receptionist_id,
    ).returning(Ticket.id)

    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")

    await session.commit()

    current_ticket_stmt = select(Ticket).where(Ticket.id == ticket_id)
    result = await session.execute(current_ticket_stmt)
    updated_ticket = result.scalar_one()
    return updated_ticket


@router.get("/{receptionist_id}/start", response_model=TicketRead)
async def start_servicing(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id, Ticket.status == "В очереди").order_by(
        Ticket.id)
    result = await session.execute(stmt)
    ticket = result.scalars().first()

    if ticket:
        ticket.status = "В процессе"
        await session.commit()

        stmt = select(Receptionist).where(Receptionist.id == ticket.receptionist_id)
        result = await session.execute(stmt)
        table_num = result.scalars().first().table_num
        ticket_data = TicketReadWS(id=ticket.id, table_num=table_num).json()

        await manager.broadcast(sendWS("screen_show", 00, ticket_data).to_json())

        return ticket
    else:
        raise HTTPException(status_code=404, detail="No ticket in queue for receptionist")


@router.get("/{receptionist_id}/next", response_model=TicketRead)
async def next_ticket(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    current_ticket_stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id, Ticket.status == "В процессе")
    result = await session.execute(current_ticket_stmt)
    current_ticket = result.scalars().first()

    if current_ticket:
        current_ticket.status = "Завершенный"

        next_ticket_stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id,
                                                Ticket.status == "В очереди").order_by(Ticket.id)
        result = await session.execute(next_ticket_stmt)
        next_ticket = result.scalars().first()

        if next_ticket:
            next_ticket.status = "В процессе"
            await session.commit()

            stmt = select(Receptionist).where(Receptionist.id == next_ticket.receptionist_id)
            result = await session.execute(stmt)
            table_num = result.scalars().first().table_num
            ticket_data = TicketReadWS(id=next_ticket.id, table_num=table_num).json()

            await manager.broadcast(sendWS("screen_show", 00, ticket_data).to_json())

            return next_ticket
        else:
            raise HTTPException(status_code=404, detail="No next ticket in queue")
    else:
        raise HTTPException(status_code=404, detail="No ticket being serviced")


@router.get("/{receptionist_id}/finish", response_model=TicketRead)
async def finish_ticket(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id, Ticket.status == "В процессе")
    result = await session.execute(stmt)
    ticket = result.scalars().first()

    if ticket:
        ticket.status = "Завершенный"
        await session.commit()

        return ticket
    else:
        raise HTTPException(status_code=404, detail="No ticket being serviced")

@router.get("/{ticket_id}/cancel", response_model=TicketRead)
async def cancel_ticket(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if ticket:
        ticket.status = "Отменен"
        await session.commit()

        ticket_data = TicketRead(
            id=ticket.id,
            email=ticket.email,
            status=ticket.status,
            date_time=ticket.date_time,
            receptionist_id=ticket.receptionist_id
        ).json()
        await manager.broadcast(sendWS("cancel_ticket", ticket.receptionist_id, ticket_data).to_json())

        return ticket
    else:
        raise HTTPException(status_code=404, detail=f"Ticket with id {ticket_id} not found")

@router.get("/{ticket_id}/pass", response_model=TicketRead)
async def pass_ticket(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketRead:
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    result = await session.execute(stmt)
    ticket = result.scalar_one_or_none()

    if ticket:
        ticket.status = "Пропущено"
        await session.commit()

        next_ticket_stmt = select(Ticket).where(
            Ticket.receptionist_id == ticket.receptionist_id,
            Ticket.status == "В очереди"
        ).order_by(Ticket.id)
        result = await session.execute(next_ticket_stmt)
        next_ticket = result.scalars().first()

        if next_ticket:
            next_ticket.status = "В процессе"
            await session.commit()

            stmt = select(Receptionist).where(Receptionist.id == next_ticket.receptionist_id)
            result = await session.execute(stmt)
            table_num = result.scalars().first().table_num
            ticket_data = TicketReadWS(id=next_ticket.id, table_num=table_num).json()

            await manager.broadcast(sendWS("screen_show", 00, ticket_data).to_json())

            return next_ticket
        else:
            raise HTTPException(status_code=404, detail="No next ticket in queue")
    else:
        raise HTTPException(status_code=404, detail=f"Ticket with id {ticket_id} not found")