from pydantic import BaseModel


class APIResponse[T](BaseModel):
    """Standard API response model."""

    success: bool
    message: str
    data: T | None = None