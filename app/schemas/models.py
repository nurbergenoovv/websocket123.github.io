from datetime import datetime

from sqlalchemy import MetaData, Table, Column, Integer, String, TIMESTAMP, ForeignKey, Boolean

metadata = MetaData()

# user = Table('user', metadata,
#              Column('id', Integer, primary_key=True),
#              Column('username', String(255), unique=True, nullable=False),
#              Column('email', String(255), unique=True, nullable=False),
#              Column('password', String(255), nullable=False),
#              Column("register_at", TIMESTAMP, default=datetime.utcnow()),
#              )
#
# task = Table('task', metadata,
#              Column('id', Integer, primary_key=True),
#              Column('title', String(255), nullable=False),
#              Column('description', String(255), nullable=True),
#              Column("user_id", Integer, ForeignKey(user.c.id), nullable=False),
#              Column("create_at", TIMESTAMP, default=datetime.utcnow()),
#              Column("is_done", Boolean, default=False)
#              )