from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database.main import get_session
from src.schemas.user_schemas import RegisterTeacher, CreateStudent, UserResponse, TokenResponse
from src.services.users import (
    register_teacher,
    create_student,
    get_user,
    get_user_by_username,
    get_user_by_email,
    get_all_users,
    delete_user,
    login,
)
from src.api.deps import CurrentUser, TeacherUser
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_teacher_account(
    details: RegisterTeacher, session: AsyncSession = Depends(get_session)
):
    if await get_user_by_username(session, details.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if await get_user_by_email(session, details.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return await register_teacher(session, details)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    # OAuth2PasswordRequestForm uses 'username' field — we treat it as email
    try:
        token = await login(session, form_data.username, form_data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return TokenResponse(access_token=token)


@router.post("/students", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_student_account(
    details: CreateStudent,
    current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
):
    if await get_user_by_username(session, details.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if await get_user_by_email(session, details.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return await create_student(session, details, created_by=current_user.id)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user


@router.get("/", response_model=list[UserResponse])
async def list_users(current_user: TeacherUser, session: AsyncSession = Depends(get_session)):
    return await get_all_users(session)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: uuid.UUID,
    current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
):
    deleted = await delete_user(session, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
