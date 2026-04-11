from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.main import get_session
from src.schemas.user_schemas import CreateUser, UserResponse
from src.services.users import create_user, get_user_by_username

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(details: CreateUser, session: AsyncSession = Depends(get_session)):
    existing = await get_user_by_username(session, details.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    return await create_user(session, details)
