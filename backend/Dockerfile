FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY app ./app
RUN uv pip install --system -e ".[dev]"

COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

RUN chmod +x scripts/start.sh

EXPOSE 8000
CMD ["./scripts/start.sh"]
