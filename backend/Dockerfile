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
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
