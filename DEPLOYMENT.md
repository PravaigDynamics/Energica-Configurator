# Deployment Guide — Energica Configurator

## Production Checklist

- [ ] PSD layers extracted to `backend/layers/`
- [ ] `backend/.env` configured with production values
- [ ] `frontend/.env.local` set to production API URL
- [ ] Redis instance provisioned (recommended for cache)
- [ ] CORS origins restricted to production domain

---

## Backend (FastAPI)

### Build & start (standard)
```bash
cd backend
pip install -r requirements.txt
uvicorn compositor_service:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY backend/layers/ ./layers/
CMD ["uvicorn", "compositor_service:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Environment variables for production
```env
LAYER_PATH=/app/layers
REDIS_URL=redis://redis:6379/0
PORT=8000
CORS_ORIGINS=https://your-domain.com
LOG_LEVEL=WARNING
JPEG_QUALITY=85
CACHE_TTL=2592000
```

---

## Frontend (Next.js)

### Build
```bash
cd frontend
npm ci
npm run build
npm start           # production server on port 3000
```

### Static export (optional)
If the frontend needs to be a static site (CDN-hosted):
```bash
# next.config.js: output: 'export'
npm run build       # outputs to /out
```

### Environment for production
```env
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

---

## Nginx reverse proxy (example)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_read_timeout 30s;
    }

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

---

## Health monitoring

```bash
# Backend health
curl https://api.your-domain.com/health

# Expected response
{"status":"ok","compositor":"ok","cache":"redis"}
```
