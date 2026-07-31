FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y nodejs npm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/src/frontend

RUN npm ci

WORKDIR /app

RUN chmod +x start.sh

CMD ["./start.sh"]
