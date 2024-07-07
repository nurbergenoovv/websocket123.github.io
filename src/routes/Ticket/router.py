from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import insert, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.routes.websocket.router import manager

from src.routes.Ticket.models import Tickets
from src.auth.models import User

from src.routes.Ticket.schemas import TicketModel, TicketCreate
from src.auth.schemas import UserRead
from src.schemas import ReturnMessage, SendToWebsocket, ResponseQueue

router = APIRouter(
    tags=["Ticket"],
    prefix="/ticket"
)


@router.post("/create", response_model=TicketModel)
async def create_ticket(new_ticket: TicketCreate, response: Response, session: AsyncSession = Depends(get_async_session)) -> TicketModel:
    query = select(User).where(User.id == new_ticket.worker_id, User.role == 'worker')
    result = await session.execute(query)
    if result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    stmt = insert(Tickets).values(
        email=new_ticket.email,
        worker_id=new_ticket.worker_id,
        status="waiting"
    ).returning(Tickets.id)
    result = await session.execute(stmt)
    await session.commit()

    created_ticket_id = result.scalar_one()

    ticket_data = TicketModel(id=created_ticket_id, email=new_ticket.email, worker_id=new_ticket.worker_id, status="waiting")

    await manager.broadcast(SendToWebsocket("new_ticket", new_ticket.worker_id, ticket_data.json()).to_json())
    response.set_cookie(key="email", value=new_ticket.email)
    return ticket_data


@router.delete("/{ticket_id}", response_model=ReturnMessage)
async def delete_ticket(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> ReturnMessage:
    query = select(Tickets).where(Tickets.id == ticket_id)
    result = await session.execute(query)
    if result.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    stmt = delete(Tickets).where(Tickets.id == ticket_id)
    await session.execute(stmt)
    await session.commit()
    return ReturnMessage(
        message="Ticket deleted",
        status="ok"
    )


@router.get("/{ticket_id}", response_model=TicketModel)
async def get_ticket_by_id(ticket_id: int,
                          session: AsyncSession = Depends(get_async_session)) -> TicketModel:
    query = select(Tickets).where(Tickets.id == ticket_id)
    result = await session.execute(query)
    ticket = result.scalars().first()

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket

@router.post("/verify", response_model=TicketModel)
async def get_ticket_by_email(request: Request,
                              session: AsyncSession = Depends(get_async_session)) -> TicketModel:
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON data")

    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    query = select(Tickets).where(Tickets.email == email)
    result = await session.execute(query)
    ticket = result.scalars().first()

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@router.get("/all/user/{user_id}", response_model=List[TicketModel])
async def get_all_tickets(user_id: int, session: AsyncSession = Depends(get_async_session)) -> List[TicketModel]:
    query1 = select(User).where(User.id == user_id, User.role == 'worker')
    result1 = await session.execute(query1)
    if result1.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    query2 = select(Tickets).where(Tickets.worker_id == user_id)
    result2 = await session.execute(query2)
    tickets = result2.scalars().all()
    if len(tickets) == 0:
        raise HTTPException(status_code=404, detail="Tickets not found")
    return tickets

@router.get("/all/user/{user_id}/waiting", response_model=List[TicketModel])
async def get_all_tickets(user_id: int, session: AsyncSession = Depends(get_async_session)) -> List[TicketModel]:
    query1 = select(User).where(User.id == user_id, User.role == 'worker')
    result1 = await session.execute(query1)
    if result1.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    query2 = select(Tickets).where(Tickets.worker_id == user_id, Tickets.status == 'waiting')
    result2 = await session.execute(query2)
    tickets = result2.scalars().all()
    if len(tickets) == 0:
        raise HTTPException(status_code=404, detail="Tickets not found")
    return tickets



@router.get("/{ticket_id}/cancel", response_model=ReturnMessage)
async def cancel_ticket(ticket_id: int,
                        session: AsyncSession = Depends(get_async_session)) -> ReturnMessage:
    query1 = select(Tickets).where(Tickets.id == ticket_id, Tickets.status == 'waiting')
    result1 = await session.execute(query1)
    ticket = result1.scalars().first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    stmt = update(Tickets).where(Tickets.id == ticket_id).values(status='cancelled')
    await session.execute(stmt)
    await session.commit()

    ticket_data = TicketModel(id=ticket.id, email=ticket.email, worker_id=ticket.worker_id, status=ticket.status)

    await manager.broadcast(SendToWebsocket("cancel_ticket", ticket.worker_id, ticket_data.json()).to_json())

    return ReturnMessage(
        message="Ticket successfully cancelled",
        status="ok"
    )

@router.get('/{ticket_id}/queue', response_model=ResponseQueue)
async def get_ticket_queue(ticket_id: int, session: AsyncSession = Depends(get_async_session)) -> ResponseQueue:
    query = select(Tickets).where(Tickets.id == ticket_id)
    result = await session.execute(query)
    ticket = result.scalars().first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    query = select(User).where(User.id == ticket.worker_id, User.role == 'worker')
    result = await session.execute(query)
    worker = result.scalars().first()
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    query = select(Tickets).where(Tickets.worker_id == worker.id, Tickets.status == 'waiting')
    result = await session.execute(query)
    tickets = result.scalars().all()

    queue = 0

    for t in tickets:
        if t.id == ticket_id:
            break
        queue += 1

    return ResponseQueue(
        queue=queue,
        worker_id=worker.id,
        ticket_id=ticket.id,
    )
