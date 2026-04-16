FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONPATH=/app

# Install astral UV runtime
COPY --from=ghcr.io/astral-sh/uv:0.6.13 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better caching
COPY ./pyproject.toml ./uv.lock /app/


RUN apt-get update \
    && apt-get install -y postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && uv sync --frozen --no-install-project --extra-index-url https://download.pytorch.org/whl/cpu


COPY ./src /app/src
COPY ./main.py /app/main.py
COPY ./migrations /app/migrations
COPY ./alembic.ini /app/alembic.ini
COPY ./resources /app/resources


CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]