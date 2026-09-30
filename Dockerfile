FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY pyproject.toml README.md requirements-api.txt ./
COPY src ./src
COPY artifacts ./artifacts
RUN pip install --no-cache-dir -r requirements-api.txt && pip install --no-cache-dir --no-deps .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn recoveriq.api:app --host 0.0.0.0 --port ${PORT}"]
