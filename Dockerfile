FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev libxslt1-dev gcc && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Use the system interpreter; prevents uv from downloading a managed Python
ENV UV_PYTHON=/usr/local/bin/python

# Dependencies layer: exact versions pinned in uv.lock.
# --frozen fails the build if pyproject.toml and uv.lock are out of sync.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

CMD ["sh", "-c", "cd /app && python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
