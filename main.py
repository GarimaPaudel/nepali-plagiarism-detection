from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.database.main import init_db
from src.api.endpoints.users import router as users_router
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Plagiarism-Detection",
    lifespan=lifespan,
)

app.include_router(users_router)


@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
