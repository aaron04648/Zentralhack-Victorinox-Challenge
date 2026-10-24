FROM python:3.12-slim

WORKDIR /app

# cloudflared für "Mit Handy scannen": öffnet nur während einer QR-Kopplung einen Tunnel (app/tunnel.py)
ARG TARGETARCH
ARG CLOUDFLARED_VERSION=2025.8.1
ADD --chmod=755 https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-${TARGETARCH} /usr/local/bin/cloudflared

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
