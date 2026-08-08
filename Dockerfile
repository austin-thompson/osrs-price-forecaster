FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

RUN uv sync --frozen --no-dev || uv sync --no-dev

ENV PATH="/app/.venv/Scripts:/app/.venv/bin:$PATH"

CMD ["uv", "run", "uvicorn", "osrs_price_forecaster.main:app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
