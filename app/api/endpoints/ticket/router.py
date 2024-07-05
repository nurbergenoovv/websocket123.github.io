from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, delete, update
from app.db.base import get_async_session
from app.api.endpoints.ticket.models import Ticket
from app.api.endpoints.ticket.schemas import TicketCreate, TicketRead, TicketReadWS, TicketDeleteRequest, TicketForPage
from typing import List
from app.api.endpoints.websocket.router import manager
from app.schemas.schemas import sendWS, EmailInput, ReturnMessage
from app.api.endpoints.receptionist.models import Receptionist

router = APIRouter(
    prefix="/ticket",
    tags=["ticket"]
)


# Get Async Session Dependency

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

        return TicketRead(
            id=ticket_id,
            date_time=ticket.date_time,
            email=ticket.email,
            status=ticket.status,
            receptionist_id=ticket.receptionist_id,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticket with id {e} not found")


async def get_queue_in_ticket(ticket: TicketRead, session: AsyncSession) -> TicketRead:
    promt = select(Ticket).where(Ticket.receptionist_id == ticket.receptionist_id, Ticket.status == 'В очереди')
    result1 = await session.execute(promt)
    if len(result1) == 0:
        return 0
    return len(result1.scalars().all())


@router.get("/{ticket_id}/page", response_model=TicketForPage)
async def get_ticket_by_id_page(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> TicketForPage:
    try:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalar_one()
        date = str(ticket.date_time)
        dt_obj = datetime.fromisoformat(date)
        readable_str = dt_obj.strftime("%Y-%m-%d %H:%M")
        ticket.date_time = readable_str

        return TicketForPage(
            id=ticket_id,
            date_time=readable_str,
            receptionist_id=ticket.receptionist_id,
            status=ticket.status,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticket with id {e} not found")


@router.post('/check_by_email', response_model=TicketRead)
async def get_by_email(response: Response, email_input: EmailInput = Body(...),
                       session: AsyncSession = Depends(get_async_session)):
    email = email_input.email
    stmt = select(Ticket).where(Ticket.email == email)
    result = await session.execute(stmt)
    ticket = result.scalars().first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/by_receptionist/{receptionist_id}", response_model=List[TicketRead])
async def get_tickets_by_receptionist_id(receptionist_id: int, session: AsyncSession = Depends(get_async_session)) -> \
        List[TicketRead]:
    try:
        stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id, Ticket.status == "В очереди")
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        return tickets
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by_receptionist/{receptionist_id}/queue")
async def get_tickets_by_receptionist_id(receptionist_id: int, session: AsyncSession = Depends(get_async_session))->int:
    try:
        stmt = select(Ticket).where(Ticket.receptionist_id == receptionist_id, Ticket.status == "В очереди")
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        if len(tickets) == 0:
            return 0
        return len(tickets)-1
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create", response_model=TicketRead)
async def create_ticket(
        new_ticket: TicketCreate,
        response: Response,
        session: AsyncSession = Depends(get_async_session),
) -> TicketRead:
    try:
        async with session.begin():
            # Create new ticket in the database
            ticket = Ticket(
                email=new_ticket.email,
                receptionist_id=new_ticket.receptionist_id,
                status="В очереди"
            )
            session.add(ticket)
            await session.flush()  # Ensure ticket is persisted and has an ID

            # Commit transaction
            await session.commit()

            # Prepare data for WebSocket broadcast
            ticket_data = TicketRead(
                id=ticket.id,
                email=new_ticket.email,
                status=ticket.status,
                receptionist_id=new_ticket.receptionist_id,
                date_time=ticket.date_time
            )
            response.set_cookie(key="email", value=new_ticket.email, httponly=True, path='/', max_age=99900)

            # Broadcast new ticket via WebSocket
            await manager.broadcast(sendWS("new_ticket", ticket.receptionist_id, ticket_data.json()).to_json())

            return ticket_data

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete")
async def delete_ticket_by_id(request: Request, session: AsyncSession = Depends(get_async_session)) -> dict:
    data = await request.json()
    email = data.get("email")
    try:
        stmt = delete(Ticket).where(Ticket.email == email)

        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ticket not found")

        await session.commit()
        return {"message": "Ticket deleted"}
    except HTTPException:
        # Re-raise HTTPExceptions to let FastAPI handle them
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{ticket_id}")
async def delete_ticket_by_idd(
        ticket_id: int,
        session: AsyncSession = Depends(get_async_session)
):
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


@router.delete("/{receptionist_id}", response_model=ReturnMessage)
async def delete_ticket_by_id(receptionist_id: int,
                              session: AsyncSession = Depends(get_async_session)) -> ReturnMessage:
    try:
        stmt = delete(Ticket).where(Ticket.receptionist_id == receptionist_id)

        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")

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

        if ticket:
            # Update its status to "В процессе"
            ticket.status = "В процессе"
            await session.commit()

            # Prepare data for WebSocket broadcast
            stmt = select(Receptionist).where(Receptionist.id == ticket.receptionist_id)
            result = await session.execute(stmt)
            table_num = result.scalars().first().table_num
            ticket_data = TicketReadWS(id=ticket.id, table_num=table_num).json()

            # Broadcast to WebSocket manager
            await manager.broadcast(sendWS("screen_show", 00, ticket_data).to_json())

            return ticket
        else:
            raise HTTPException(status_code=404, detail="No ticket in queue for receptionist")

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

        if current_ticket:
            # Update its status to "Завершенный"
            current_ticket.status = "Завершенный"

            # Find the next ticket in queue for the receptionist
            next_ticket_stmt = select(Ticket).where(
                Ticket.receptionist_id == receptionist_id,
                Ticket.status == "В очереди"
            ).order_by(Ticket.id)

            result = await session.execute(next_ticket_stmt)
            next_ticket = result.scalars().first()

            if next_ticket:
                # Update its status to "В процессе"
                next_ticket.status = "В процессе"
                await session.commit()

                # Prepare data for WebSocket broadcast
                stmt = select(Receptionist).where(Receptionist.id == next_ticket.receptionist_id)
                result = await session.execute(stmt)
                table_num = result.scalars().first().table_num
                ticket_data = TicketReadWS(id=next_ticket.id, table_num=table_num).json()

                # Broadcast to WebSocket manager
                await manager.broadcast(sendWS("screen_show", 00, ticket_data).to_json())

                return next_ticket
            else:
                raise HTTPException(status_code=404, detail="No next ticket in queue")
        else:
            raise HTTPException(status_code=404, detail="No ticket being serviced")

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

        if ticket:
            # Update its status to "Завершенный"
            ticket.status = "Завершенный"
            await session.commit()

            return ticket
        else:
            raise HTTPException(status_code=404, detail="No ticket being serviced")

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

        if ticket:
            # Update the ticket's status to "Отменен"
            ticket.status = "Отменен"
            await session.commit()

            # Prepare data for WebSocket broadcast
            ticket_data = TicketRead(id=ticket.id, email=ticket.email, status=ticket.status, date_time=ticket.date_time,
                                     receptionist_id=ticket.receptionist_id).json()

            # Broadcast to WebSocket manager
            await manager.broadcast(sendWS("cancel_ticket", ticket.receptionist_id, ticket_data).to_json())

            return ticket
        else:
            raise HTTPException(status_code=404, detail=f"Ticket with id {ticket_id} not found")

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

        if ticket:
            # Update the ticket's status to "Пропущено"
            ticket.status = "Пропущено"
            await session.commit()
            next_ticket_stmt = select(Ticket).where(
                Ticket.receptionist_id == ticket.receptionist_id,
                Ticket.status == "В очереди"
            ).order_by(Ticket.id)

            result = await session.execute(next_ticket_stmt)
            next_ticket = result.scalars().first()

            if next_ticket:
                # Update its status to "В процессе"
                next_ticket.status = "В процессе"
                await session.commit()

                # Prepare data for WebSocket broadcast
                stmt = select(Receptionist).where(Receptionist.id == next_ticket.receptionist_id)
                result = await session.execute(stmt)
                table_num = result.scalars().first().table_num
                ticket_data = TicketReadWS(id=next_ticket.id, table_num=table_num).json()

                # Broadcast to WebSocket manager
                await manager.broadcast(sendWS("screen_show", 00, ticket_data).to_json())

                return ticket
        else:
            raise HTTPException(status_code=404, detail=f"Ticket with id {ticket_id} not found")

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
