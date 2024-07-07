from typing import List

from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi_users import FastAPIUsers

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.base_config import auth_backend
from src.auth.models import User
from src.routes.Ticket.models import Tickets

from src.database import async_session_maker, get_async_session
from src.auth.manager import get_user_manager
from src.routes.websocket.router import manager

from src.schemas import ReturnMessage, WorkerInformation, SendToWebsocket
from src.routes.Ticket.schemas import TicketModel

router = APIRouter(
    prefix="/workers",
    tags=["workers"],
)

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)


@router.get("/", response_model=List[WorkerInformation])
async def get_workers(
        session: AsyncSession = Depends(get_async_session),
) -> List[WorkerInformation]:
    workers_list = []

    query = select(User).where(User.role == 'worker')
    result = await session.execute(query)
    workers = result.scalars().all()

    for worker in workers:
        query = select(Tickets).where(Tickets.worker_id == worker.id, Tickets.status == 'waiting')
        result = await session.execute(query)
        tickets = result.scalars().all()

        workers_list.append(
            WorkerInformation(
                id=worker.id,
                first_name=worker.first_name,
                last_name=worker.last_name,
                email=worker.email,
                queue=len(tickets)
            )
        )
    return workers_list


@router.get("/ticket/next", response_model=TicketModel)
async def get_next_ticket(
    user: User = Depends(fastapi_users.current_user()),
    session: AsyncSession = Depends(get_async_session)
) -> TicketModel:
    if user.role != 'worker':
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this operation.",
        )

    query = select(Tickets).where(Tickets.worker_id == user.id, Tickets.status == 'processing')
    result = await session.execute(query)
    prosessed_ticket = result.scalars().first()
    if prosessed_ticket:
        stmt = update(Tickets).where(Tickets.id == prosessed_ticket.id).values(status="finised")
        await session.execute(stmt)



    query = select(Tickets).where(Tickets.worker_id == user.id, Tickets.status == 'waiting').order_by(Tickets.id)
    result = await session.execute(query)
    ticket = result.scalars().first()
    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="No tickets found",
        )
    else:
        stmt = update(Tickets).where(Tickets.id == ticket.id).values(status="processing")
        await session.execute(stmt)
        ticket_data = TicketModel(id=ticket.id, email=ticket.email, worker_id=ticket.worker_id, status=ticket.status)

        await manager.broadcast(SendToWebsocket("show_screen", 00, ticket_data.json()).to_json())
    await session.commit()  # Ensure the change is committed to the database

    return ticket


@router.get("/ticket/finish", response_model=TicketModel)
async def finish_ticket(
        user: User = Depends(fastapi_users.current_user()),
        session: AsyncSession = Depends(get_async_session)
)-> TicketModel:
    if user.role != 'worker':
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this operation."
        )
    query = select(Tickets).where(Tickets.worker_id == user.id, Tickets.status == 'processing')
    result = await session.execute(query)
    prosessed_ticket = result.scalars().first()

    if prosessed_ticket is None:
        raise HTTPException(
            status_code=403,
            detail="No tickets found",
        )

    stmt = update(Tickets).where(Tickets.id == prosessed_ticket.id).values(status="finished")
    result = await session.execute(stmt)
    await session.commit()


    return TicketModel(
        id=prosessed_ticket.id,
        email=prosessed_ticket.email,
        worker_id=prosessed_ticket.worker_id,
        status="finished",
    )

