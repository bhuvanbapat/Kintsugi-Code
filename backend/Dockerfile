FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" pydantic pydantic-settings httpx \
    tree-sitter tree-sitter-language-pack pytest pytest-asyncio

COPY app ./app
COPY tests ./tests
COPY scripts ./scripts

ENV CODEFORGE_ENVIRONMENT=production
# Keep the SQLite database on the mounted volume so indexed data survives.
ENV CODEFORGE_SQLITE_PATH=/app/data/codeforge.db
RUN mkdir -p /app/data
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
