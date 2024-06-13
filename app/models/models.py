from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, TIMESTAMP, ForeignKey

from app.auth.models import user

metadata = MetaData()

from datetime import datetime

task = Table(
    "task",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(255), nullable=False),
    Column("description", String(255), nullable=True),
    Column("done", Boolean, default=False),
    Column("created_at", TIMESTAMP, default=datetime.utcnow, nullable=False),  # Ensure created_at is not nullable
    Column("user_id", Integer, ForeignKey(user.c.id), nullable=False),
)
