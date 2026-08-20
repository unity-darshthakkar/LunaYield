# ---------- Frontend build ----------
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- Backend runtime ----------
FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app

RUN pip install --no-cache-dir /app/backend

COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

ENV SERVE_FRONTEND=true
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]