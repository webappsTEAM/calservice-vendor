# Production Dockerfile for CalTrack Workforce Backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for psycopg2 and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Static and media directories
RUN mkdir -p /app/media /app/staticfiles

# Run as non-privileged application user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

CMD ["gunicorn", "workforce_core.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001", "-w", "4", "--timeout", "120"]
