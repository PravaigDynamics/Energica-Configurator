# Energica Motorcycle Configurator

Interactive layer-based motorcycle configurator for Energica's four models:
**EVA · ESSESSE9 · EGO · RIBELLE**

---

## Architecture

```
Browser (Next.js)  →  POST /configure  →  FastAPI (Python)  →  Pillow (composite)
                       GET /config/{model}                    →  Layer PNGs on disk
```

### Stack
| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript strict |
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Image processing | Pillow (RGBA compositing) |
| PSD extraction | psd-tools |
| Cache | Redis (optional) / in-memory fallback |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- (Optional) Redis

### One-command setup

```bash
bash scripts/setup.sh
```

### Extract PSD layers

```bash
cd backend && source .venv/bin/activate

python extract_psd.py /absolute/path/EVA.psd        --model eva
python extract_psd.py /absolute/path/ESSESSE9.psd   --model essesse9
python extract_psd.py /absolute/path/EGO.psd        --model ego
python extract_psd.py /absolute/path/RIBELLE.psd    --model ribelle
```

Or use the batch script:

```bash
bash scripts/extract-all.sh /path/EVA.psd /path/ESSESSE9.psd /path/EGO.psd /path/RIBELLE.psd
```

### Start the services

**Backend** (terminal 1):
```bash
cd backend
source .venv/bin/activate
uvicorn compositor_service:app --reload --port 8000
```

**Frontend** (terminal 2):
```bash
cd frontend
npm run dev    # http://localhost:3000
```

Test page with all models: **http://localhost:3000/test**

---

## API Reference

### `GET /health`
```json
{ "status": "ok", "compositor": "ok", "cache": "memory" }
```

### `GET /config/{model}`
Returns the full layer schema including groups, rules, and default visibility.

**Models:** `eva` · `essesse9` · `ego` · `ribelle`

### `POST /configure`
Composite layers into a preview image.

```json
{
  "model": "eva",
  "layers": ["frame", "base_stealth", "ohlins"],
  "format": "jpeg",
  "quality": 85
}
```
Returns: `image/jpeg` or `image/png`

### `POST /validate`
Validate a layer selection without rendering.

```json
{ "model": "eva", "layers": ["frame", "base_stealth"] }
```
Returns: `{ "valid": true, "error": null }`

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Default | Description |
|----------|---------|-------------|
| `LAYER_PATH` | `./layers` | Path to extracted layer directories |
| `REDIS_URL` | (empty) | Redis connection URL (optional) |
| `PORT` | `8000` | HTTP port |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed origins |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `JPEG_QUALITY` | `85` | Output JPEG quality (1-95) |
| `CACHE_TTL` | `2592000` | Cache TTL in seconds (30 days) |

### Frontend (`frontend/.env.local`)
| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Compositor service URL |

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

---

## Brand Guidelines

This product follows the **Energica Visual Branding Toolkit (2026)**:

- **Colors:** Energica Green `#78BE20` (accent only), Black/White/Graphite (surfaces)
- **Typography:** Barlow Condensed (headings, UI labels), IBM Plex Sans (body)
- **Tone:** Premium, technical, minimal — no decorative elements
- **Tagline:** "Progress, Ridden."
- **Dark mode:** Fully supported via `prefers-color-scheme`

All CSS values are defined as tokens in `frontend/styles/energica-theme.css`.
Components must use `var(--token-name)` exclusively — no hardcoded color values.

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment instructions.
