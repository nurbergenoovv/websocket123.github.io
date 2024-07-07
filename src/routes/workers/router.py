from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from torch.distributed.elastic.agent.server import Worker

from src.auth.models import User
from src.routes.Ticket.models import Tickets

from src.database import async_session_maker, get_async_session

from src.schemas import ReturnMessage, WorkerInformation
from src.routes.Ticket.schemas import TicketModel

router = APIRouter(
    prefix="/workers",
    tags=["workers"],
)

@router.get("/", response_model=List[WorkerInformation])
async def get_workers(
        session: AsyncSession = Depends(get_async_session),
)-> List[WorkerInformation]:

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



