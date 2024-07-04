# rate/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, func, TIMESTAMP
from app.db.base import Base
# from app.api.endpoints.receptionist.models import Receptionist

class Rate(Base):
    __tablename__ = "rates"
    id = Column(Integer, primary_key=True, index=True)
    rate = Column(Integer, nullable=False)
    # receptionist_id = Column(Integer, ForeignKey(Receptionist.id), nullable=False)
    date_time = Column(TIMESTAMP, nullable=False, server_default=func.now())

# rates = Table(
#     "rates",
#     metadata,
#     Column("id", Integer, primary_key=True),
#     Column("receptionist_id", Integer, ForeignKey(Receptionist.id), nullable=False),
#     Column("rate", Integer, nullable=False),
#     Column("dateTime", TIMESTAMP, default=datetime.utcnow, nullable=False),
# )
