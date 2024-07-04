import sys

from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from app.api.endpoints.receptionist.models import Receptionist  # Adjust this import as needed
from app.db.base import Base

sys.path.append('../../../../')

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    status = Column(String(255), nullable=False)
    receptionist_id = Column(Integer, ForeignKey(Receptionist.id), nullable=False)  # Adjust ForeignKey as per Receptionist model
    date_time = Column(TIMESTAMP, nullable=False, server_default=func.now())
