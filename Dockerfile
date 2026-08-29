# Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Snapshot Git info, then drop .git so /version uses version.json (not live Git).
RUN python3 scripts/generate_version.py && rm -rf /app/.git

CMD ["python", "main.py"]
