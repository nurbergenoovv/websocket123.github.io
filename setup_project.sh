#!/bin/bash

# Создание структуры директорий
mkdir -p app
mkdir -p app/routers
mkdir -p app/routers/users
mkdir -p app/routers/bookings
mkdir -p app/routers/tickets
mkdir -p app/routers/windows
mkdir -p app/routers/auth
mkdir -p app/crud

# Создание файлов и добавление кода

# app/__init__.py
touch app/__init__.py

# app/main.py
cat <<EOF > app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.routers import users, bookings, tickets, windows, auth

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(windows.router, prefix="/windows", tags=["windows"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# WebSocket для обновления очереди в реальном времени
connected_clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for client in connected_clients:
                await client.send_text(data)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
EOF

# app/config.py
cat <<EOF > app/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_TLS: bool
    MAIL_SSL: bool
    SECRET_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
EOF

# app/auth.py
cat <<EOF > app/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.config import settings
from app.database import get_db
from app.routers.users.models import User

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not pwd_context.verify(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.role == "inactive":
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
EOF

# app/mail.py
cat <<EOF > app/mail.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_TLS=settings.MAIL_TLS,
    MAIL_SSL=settings.MAIL_SSL,
    USE_CREDENTIALS=True
)

async def send_reset_password_email(email: str, token: str):
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"Here is your password reset token: {token}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)
EOF

# app/database.py
cat <<EOF > app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}/{settings.DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOF

# app/routers/__init__.py
touch app/routers/__init__.py

# app/routers/users/models.py
cat <<EOF > app/routers/users/models.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)

    bookings = relationship("Booking", back_populates="user")
    windows = relationship("Window", back_populates="user")
EOF

# app/routers/users/schemas.py
cat <<EOF > app/routers/users/schemas.py
from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str

class UserUpdate(BaseModel):
    email: str
    password: str

class ResetPasswordRequest(BaseModel):
    email: str

class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class ChangeEmail(BaseModel):
    new_email: str
EOF

# app/routers/users/crud.py
cat <<EOF > app/routers/users/crud.py
from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate, UserUpdate
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(db: Session, user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def update_user(db: Session, user_id: int, user_update: UserUpdate):
    user = get_user(db, user_id)
    if user:
        user.email = user_update.email
        user.hashed_password = pwd_context.hash(user_update.password)
        db.commit()
        db.refresh(user)
    return user

def delete_user(db: Session, user_id: int):
    user = get_user(db, user_id)
    if user:
        db.delete(user)
        db.commit()
    return user
EOF

# app/routers/users/routes.py
cat <<EOF > app/routers/users/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from app.database import get_db
from app.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.UserCreate)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db=db, user=user)

@router.get("/me/", response_model=schemas.UserCreate)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@router.put("/{user_id}", response_model=schemas.UserUpdate)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    return crud.update_user(db=db, user_id=user_id, user_update=user)

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return crud.delete_user(db=db, user_id=user_id)
EOF

# app/routers/bookings/models.py
cat <<EOF > app/routers/bookings/models.py
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    booking_time = Column(DateTime)
    status = Column(String, default='pending')

    user = relationship("User", back_populates="bookings")
    tickets = relationship("Ticket", back_populates="booking")
EOF

# app/routers/bookings/schemas.py
cat <<EOF > app/routers/bookings/schemas.py
from pydantic import BaseModel
from datetime import datetime

class BookingCreate(BaseModel):
    user_id: int
    booking_time: datetime
    status: str

class BookingUpdate(BaseModel):
    user_id: int
    booking_time: datetime
    status: str
EOF

# app/routers/bookings/crud.py
cat <<EOF > app/routers/bookings/crud.py
from sqlalchemy.orm import Session
from .models import Booking
from .schemas import BookingCreate, BookingUpdate

def create_booking(db: Session, booking: BookingCreate):
    db_booking = Booking(
        user_id=booking.user_id,
        booking_time=booking.booking_time,
        status=booking.status
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

def get_booking(db: Session, booking_id: int):
    return db.query(Booking).filter(Booking.id == booking_id).first()

def update_booking(db: Session, booking_id: int, booking_update: BookingUpdate):
    booking = get_booking(db, booking_id)
    if booking:
        booking.user_id = booking_update.user_id
        booking.booking_time = booking_update.booking_time
        booking.status = booking_update.status
        db.commit()
        db.refresh(booking)
    return booking

def delete_booking(db: Session, booking_id: int):
    booking = get_booking(db, booking_id)
    if booking:
        db.delete(booking)
        db.commit()
    return booking
EOF

# app/routers/bookings/routes.py
cat <<EOF > app/routers/bookings/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from app.database import get_db
from app.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.BookingCreate)
def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    return crud.create_booking(db=db, booking=booking)

@router.get("/{booking_id}", response_model=schemas.BookingCreate)
def read_booking(booking_id: int, db: Session = Depends(get_db)):
    db_booking = crud.get_booking(db, booking_id=booking_id)
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return db_booking

@router.put("/{booking_id}", response_model=schemas.BookingUpdate)
def update_booking(booking_id: int, booking: schemas.BookingUpdate, db: Session = Depends(get_db)):
    return crud.update_booking(db=db, booking_id=booking_id, booking_update=booking)

@router.delete("/{booking_id}")
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    return crud.delete_booking(db=db, booking_id=booking_id)
EOF

# app/routers/tickets/models.py
cat <<EOF > app/routers/tickets/models.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(Integer, nullable=False)
    email = Column(String, nullable=True)
    status = Column(String, default='waiting')
    booking_id = Column(Integer, ForeignKey('bookings.id'))
    window_id = Column(Integer, ForeignKey('windows.id'))

    booking = relationship("Booking", back_populates="tickets")
    window = relationship("Window", back_populates="tickets")
EOF

# app/routers/tickets/schemas.py
cat <<EOF > app/routers/tickets/schemas.py
from pydantic import BaseModel

class TicketCreate(BaseModel):
    ticket_number: int
    email: str
    status: str
    booking_id: int
    window_id: int

class TicketUpdate(BaseModel):
    status: str
    window_id: int
EOF

# app/routers/tickets/crud.py
cat <<EOF > app/routers/tickets/crud.py
from sqlalchemy.orm import Session
from .models import Ticket
from .schemas import TicketCreate, TicketUpdate

def create_ticket(db: Session, ticket: TicketCreate):
    db_ticket = Ticket(
        ticket_number=ticket.ticket_number,
        email=ticket.email,
        status=ticket.status,
        booking_id=ticket.booking_id,
        window_id=ticket.window_id
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

def get_ticket(db: Session, ticket_id: int):
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()

def update_ticket(db: Session, ticket_id: int, ticket_update: TicketUpdate):
    ticket = get_ticket(db, ticket_id)
    if ticket:
        ticket.status = ticket_update.status
        ticket.window_id = ticket_update.window_id
        db.commit()
        db.refresh(ticket)
    return ticket

def delete_ticket(db: Session, ticket_id: int):
    ticket = get_ticket(db, ticket_id)
    if ticket:
        db.delete(ticket)
        db.commit()
    return ticket
EOF

# app/routers/tickets/routes.py
cat <<EOF > app/routers/tickets/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from app.database import get_db
from app.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.TicketCreate)
def create_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    return crud.create_ticket(db=db, ticket=ticket)

@router.get("/{ticket_id}", response_model=schemas.TicketCreate)
def read_ticket(ticket_id: int, db: Session = Depends(get_db)):
    db_ticket = crud.get_ticket(db, ticket_id=ticket_id)
    if db_ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_ticket

@router.put("/{ticket_id}", response_model=schemas.TicketUpdate)
def update_ticket(ticket_id: int, ticket: schemas.TicketUpdate, db: Session = Depends(get_db)):
    return crud.update_ticket(db=db, ticket_id=ticket_id, ticket_update=ticket)

@router.delete("/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return crud.delete_ticket(db=db, ticket_id=ticket_id)
EOF

# app/routers/windows/models.py
cat <<EOF > app/routers/windows/models.py
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Window(Base):
    __tablename__ = 'windows'

    id = Column(Integer, primary_key=True, index=True)
    window_number = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="windows")
    tickets = relationship("Ticket", back_populates="window")
EOF

# app/routers/windows/schemas.py
cat <<EOF > app/routers/windows/schemas.py
from pydantic import BaseModel

class WindowCreate(BaseModel):
    window_number: int
    user_id: int

class WindowUpdate(BaseModel):
    window_number: int
EOF

# app/routers/windows/crud.py
cat <<EOF > app/routers/windows/crud.py
from sqlalchemy.orm import Session
from .models import Window
from .schemas import WindowCreate, WindowUpdate

def create_window(db: Session, window: WindowCreate):
    db_window = Window(
        window_number=window.window_number,
        user_id=window.user_id
    )
    db.add(db_window)
    db.commit()
    db.refresh(db_window)
    return db_window

def get_window(db: Session, window_id: int):
    return db.query(Window).filter(Window.id == window_id).first()

def update_window(db: Session, window_id: int, window_update: WindowUpdate):
    window = get_window(db, window_id)
    if window:
        window.window_number = window_update.window_number
        db.commit()
        db.refresh(window)
    return window

def delete_window(db: Session, window_id: int):
    window = get_window(db, window_id)
    if window:
        db.delete(window)
        db.commit()
    return window
EOF

# Продолжение app/routers/windows/routes.py
cat <<EOF > app/routers/windows/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from app.database import get_db
from app.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=schemas.WindowCreate)
def create_window(window: schemas.WindowCreate, db: Session = Depends(get_db)):
    return crud.create_window(db=db, window=window)

@router.get("/{window_id}", response_model=schemas.WindowCreate)
def read_window(window_id: int, db: Session = Depends(get_db)):
    db_window = crud.get_window(db, window_id=window_id)
    if db_window is None:
        raise HTTPException(status_code=404, detail="Window not found")
    return db_window

@router.put("/{window_id}", response_model=schemas.WindowUpdate)
def update_window(window_id: int, window: schemas.WindowUpdate, db: Session = Depends(get_db)):
    return crud.update_window(db=db, window_id=window_id, window_update=window)

@router.delete("/{window_id}")
def delete_window(window_id: int, db: Session = Depends(get_db)):
    return crud.delete_window(db=db, window_id=window_id)
EOF

# app/routers/auth/schemas.py
cat <<EOF > app/routers/auth/schemas.py
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserInDB(BaseModel):
    username: str
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str
EOF

# app/routers/auth/routes.py
cat <<EOF > app/routers/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.auth import authenticate_user, create_access_token, get_current_active_user
from app.database import get_db
from app.routers.users import crud, models, schemas

router = APIRouter()

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/", response_model=schemas.UserCreate)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db=db, user=user)

@router.get("/users/me/", response_model=schemas.UserCreate)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user
EOF

# Создание .env
cat <<EOF > .env
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_password
MAIL_FROM=your_email@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.example.com
MAIL_TLS=True
MAIL_SSL=False
SECRET_KEY=your_secret_key
DB_USERNAME=your_db_username
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_NAME=queue_rental_db
EOF

# Создание requirements.txt
cat <<EOF > requirements.txt
fastapi
uvicorn
sqlalchemy
asyncpg
psycopg2-binary
passlib
fastapi-mail
python-jose
pydantic
EOF