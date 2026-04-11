from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.models.users import Users
from src.schemas.user_schemas import CreateUser
import bcrypt


async def create_user(session: AsyncSession, details: CreateUser) -> Users:
    hashed_password = bcrypt.hashpw(details.password.encode(), bcrypt.gensalt()).decode()
    user = Users(
        username=details.username,
        hashed_password=hashed_password,
        role=details.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> Users | None:
    result = await session.exec(select(Users).where(Users.username == username))
    return result.first()
