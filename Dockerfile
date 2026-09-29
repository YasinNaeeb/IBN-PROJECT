FROM python:3.11-slim

WORKDIR /app

# System deps needed by paramiko/cryptography wheels on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Each service overrides CMD via docker-compose.yml.
# Defaulting to the engine so `docker build && docker run` alone works.
EXPOSE 8000 5000
CMD ["python", "-m", "uvicorn", "core.engine:app", "--host", "0.0.0.0", "--port", "8000"]
