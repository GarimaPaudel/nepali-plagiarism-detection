from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.main import get_session
from src.schemas.user_schemas import CreateUser, UserResponse
from src.services.users import create_user, get_user_by_username, get_user, get_all_users, delete_user
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(details: CreateUser, session: AsyncSession = Depends(get_session)):
    existing = await get_user_by_username(session, details.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    return await create_user(session, details)


@router.get("/", response_model=list[UserResponse])
async def list_users(session: AsyncSession = Depends(get_session)):
    return await get_all_users(session)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    deleted = await delete_user(session, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
