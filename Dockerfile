# Universal container for ALDash (FastAPI). Works on Koyeb, Fly.io, Render,
# Railway, Hugging Face Spaces — anything that runs a Docker image.
FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (secrets are NOT copied — see .dockerignore; pass them as env vars).
COPY . .

ENV PORT=8000
EXPOSE 8000

# Honour the platform's $PORT if it sets one, else default to 8000.
CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
