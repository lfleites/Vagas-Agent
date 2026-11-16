FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir playwright requests
RUN playwright install --with-deps chromium

COPY app.py .

CMD ["python", "app.py"]
