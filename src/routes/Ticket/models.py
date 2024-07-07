
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from src.auth.models import User

from src.database import Base

class Tickets(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False)
    status = Column(String, nullable=False, default='waiting')
    worker_id = Column(Integer, ForeignKey(User.id))

