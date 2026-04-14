from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt import jwk
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.database.models.users import UserRole, Users
from src.schemas.user_schemas import RegisterTeacher, CreateStudent
import uuid


async def get_user_by_email(session: AsyncSession, email: str) -> Users | None:
    result = await session.exec(select(Users).where(Users.email == email))
    return result.first()


async def get_user_by_username(session: AsyncSession, username: str) -> Users | None:
    result = await session.exec(select(Users).where(Users.username == username))
    return result.first()


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> Users | None:
    result = await session.exec(select(Users).where(Users.id == user_id))
    return result.first()


async def get_all_users(session: AsyncSession) -> list[Users]:
    result = await session.exec(select(Users))
    return list(result.all())


async def register_teacher(session: AsyncSession, details: RegisterTeacher) -> Users:
    hashed_password = bcrypt.hashpw(details.password.encode(), bcrypt.gensalt()).decode()
    user = Users(
        username=details.username,
        email=details.email,
        hashed_password=hashed_password,
        role=UserRole.teacher,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_student(
    session: AsyncSession, details: CreateStudent, created_by: uuid.UUID
) -> Users:
    hashed_password = bcrypt.hashpw(details.password.encode(), bcrypt.gensalt()).decode()
    user = Users(
        username=details.username,
        email=details.email,
        hashed_password=hashed_password,
        role=UserRole.student,
        created_by=created_by,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def login(session: AsyncSession, email: str, password: str) -> str:
    user = await get_user_by_email(session, email)
    if not user or not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        raise ValueError("Invalid email or password")
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    secret_key = jwk.OctetJWK(settings.JWT_SECRET_KEY.encode())
    token = jwt.JWT().encode(
        {"sub": str(user.id), "role": user.role, "exp": int(expire.timestamp())},
        secret_key,
        alg=settings.JWT_ALGORITHM,
    )
    return token


async def delete_user(session: AsyncSession, user_id: uuid.UUID) -> bool:
    user = await get_user(session, user_id)
    if not user:
        return False
    await session.delete(user)
    await session.commit()
    return True
