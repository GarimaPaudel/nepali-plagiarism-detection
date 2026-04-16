from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DEBUG: bool = True
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # ML / plagiarism detection
    MODEL_PATH: str = "/app/model"
    CORPUS_PATH: str = "/app/corpus"
    UPLOADS_PATH: str = "/app/uploads"
    STOPWORDS_PATH: str = "/app/resources/nepali_stopwords.txt"
    FONT_PATH: str = "/app/resources/NotoSansDevanagari-Bold.ttf"
    PLAGIARISM_THRESHOLD: float = 0.5

    # Celery / Redis
    REDIS_URL: str = "redis://plagiarism_redis:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

settings = Settings()