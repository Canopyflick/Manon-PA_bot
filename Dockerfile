# Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*


COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
