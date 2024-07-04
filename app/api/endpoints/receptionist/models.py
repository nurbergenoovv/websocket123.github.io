# receptionist/models.py
import sys

# sys.path.append("../../../../")
from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Receptionist(Base):
    __tablename__ = "receptionists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    photo = Column(String, nullable=False)
    table_num = Column(Integer, nullable=False)

