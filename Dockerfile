FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py .
RUN pip install --no-cache-dir playwright requests
RUN playwright install --with-deps chromium

CMD ["python", "app.py"]
