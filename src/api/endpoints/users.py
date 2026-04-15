from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from loguru import logger

from src.core.exception import ConflictException, CustomException, NotFoundException, UnauthorizedException
from src.core.responses import APIResponse
from src.database.main import get_session
from src.schemas.user_schemas import RegisterTeacher, CreateStudent, UserResponse, TokenResponse
from src.services.users import (
    register_teacher,
    create_student,
    get_user,
    get_all_users,
    delete_user,
    login,
)
from src.api.deps import CurrentUser, TeacherUser
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register_teacher_account(
    details: RegisterTeacher, session: AsyncSession = Depends(get_session)
) -> APIResponse:   
    try:
        user = await register_teacher(session, details)
        return APIResponse(
            success=True,
            message= "Teacher registered successfully",
            data=user
        )
    except ConflictException as e:
        logger.error(f"Email conflict registering account: {e!s}")
        raise

    except Exception as e:
        logger.error(f"Error while registering account: {e!s}")
        raise CustomException(message="Error while registering account.") from e


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    # OAuth2PasswordRequestForm uses 'username' field — we treat it as email
    try:
        token = await login(session, form_data.username, form_data.password)
        return APIResponse(
            success=True,
            message="Loggeg in successfully",
            data=TokenResponse(access_token=token)
        )

    except UnauthorizedException as e:
        logger.error(f"Error logging into the account: {e!s}")
        raise

    except Exception as e:
        logger.error(f"Error logging into the account: {e!s}")
        raise CustomException(message="Error logging into the account") from e


@router.post("/students", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_student_account(
    details: CreateStudent,
    current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        user = await create_student(session, details, created_by=current_user.id)
        return APIResponse(success=True, message="Student account created successfully", data=user)
    except ConflictException:
        raise
    except Exception as e:
        logger.error(f"Error creating student: {e!s}")
        raise CustomException(message="Error while creating student account") from e


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(current_user: CurrentUser) -> APIResponse:
    return APIResponse(success=True, message="User retrieved successfully", data=current_user)


@router.get("/", response_model=APIResponse[list[UserResponse]])
async def list_users(
    _current_user: TeacherUser, session: AsyncSession = Depends(get_session)
) -> APIResponse:
    try:
        users = await get_all_users(session)
        return APIResponse(success=True, message="Users retrieved successfully", data=users)
    except Exception as e:
        logger.error(f"Error listing users: {e!s}")
        raise CustomException(message="Error retrieving users") from e


@router.get("/{user_id}", response_model=APIResponse[UserResponse])
async def get_user_by_id(
    user_id: uuid.UUID,
    _current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        user = await get_user(session, user_id)
        if not user:
            raise NotFoundException(message="User not found")
        return APIResponse(success=True, message="User retrieved successfully", data=user)
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e!s}")
        raise CustomException(message="Error retrieving user") from e


@router.delete("/{user_id}", response_model=APIResponse)
async def remove_user(
    user_id: uuid.UUID,
    _current_user: TeacherUser,
    session: AsyncSession = Depends(get_session),
) -> APIResponse:
    try:
        deleted = await delete_user(session, user_id)
        if not deleted:
            raise NotFoundException(message="User not found")
        return APIResponse(success=True, message="User deleted successfully")
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e!s}")
        raise CustomException(message="Error deleting user") from e
