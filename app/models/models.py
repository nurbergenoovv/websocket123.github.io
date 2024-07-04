from sqlalchemy import Table, Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint
from datetime import datetime
from app.db.base import metadata
# from app.api.endpoints.receptionist.models import Receptionist


# receptionists = Table(
#     "receptionists",
#     metadata,
#     Column("id", Integer, primary_key=True),
#     Column("first_name", String(255), nullable=False),
#     Column("last_name", String(255), nullable=False),
#     Column("email", String(255), nullable=False, unique=True),
#     Column("photo", String(255), nullable=False),
#     Column("table_num", Integer, nullable=False),
# )

# tickets = Table(
#     "tickets",
#     metadata,
#     Column("id", Integer, primary_key=True),
#     Column("email", String(255), nullable=False),
#     Column("status", String(255), nullable=False),
#     Column("receptionist_id", Integer, ForeignKey(Receptionist.id), nullable=False),
#     Column("dateTime", TIMESTAMP, default=datetime.utcnow, nullable=False),
# )
#
# rates = Table(
#     "rates",
#     metadata,
#     Column("id", Integer, primary_key=True),
#     Column("receptionist_id", Integer, ForeignKey(Receptionist.id), nullable=False),
#     Column("rate", Integer, nullable=False),
#     Column("dateTime", TIMESTAMP, default=datetime.utcnow, nullable=False),
# )