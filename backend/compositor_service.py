from __future__ import annotations

"""
Energica Compositor Service

FastAPI application that composites PSD layers into a single preview image
for the Energica Motorcycle Configurator.

Run:
    uvicorn compositor_service:app --reload --port 8000
"""

import hashlib
import io
import json
import logging
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Literal, Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("compositor")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    layer_path: Path = Path("./layers")
    redis_url: str = ""
    port: int = 8000
    cors_origins: str = "*"
    log_level: str = "INFO"
    jpeg_quality: int = 85
    cache_ttl: int = 2592000  # 30 days

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# ---------------------------------------------------------------------------
# Blob layer resolver
# ---------------------------------------------------------------------------

# When running on Vercel, layer PNGs are stored in Vercel Blob Storage.
# Set BLOB_BASE_URL to the store's public CDN root (e.g.
# https://<id>.public.blob.vercel-storage.com). The compositor will
# download each layer to /tmp on first use and cache it for warm invocations.
_BLOB_BASE = os.getenv("BLOB_BASE_URL", "").rstrip("/")
_BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "")
_TMP_LAYERS = Path("/tmp/energica-layers")


def _resolve_layer_path(model: str, filename: str, local_path: Path) -> Path:
    """Return a readable path for a layer PNG.

    Tries the local filesystem first (works in dev and Docker).
    Falls back to downloading from Vercel Blob Storage into /tmp when the
    file is absent and BLOB_BASE_URL is configured.
    """
    if local_path.exists():
        return local_path

    if not _BLOB_BASE:
        return local_path  # will be logged as missing by the compositor

    cached = _TMP_LAYERS / model / filename
    if cached.exists():
        return cached

    cached.parent.mkdir(parents=True, exist_ok=True)
    url = f"{_BLOB_BASE}/layers/{model}/{filename}"
    try:
        req = urllib.request.Request(url)
        if _BLOB_TOKEN:
            req.add_header("Authorization", f"Bearer {_BLOB_TOKEN}")
        with urllib.request.urlopen(req) as resp:
            cached.write_bytes(resp.read())
        logger.debug("Downloaded layer from Blob: %s", url)
    except Exception as exc:
        logger.warning("Failed to fetch layer from Blob (%s): %s", url, exc)
        return local_path  # compositor will log it as missing

    return cached


_prefetch_pool = ThreadPoolExecutor(max_workers=8)


def _prefetch_model_layers(model: str, config: ConfigSchema) -> None:
    """Download all layer PNGs for a model to /tmp in parallel.

    Called as a background task on GET /config so layers are warm by the
    time the first POST /configure arrives.
    """
    if not _BLOB_BASE:
        return
    layer_dir = settings.layer_path / model

    def _fetch(filename: str) -> None:
        _resolve_layer_path(model, filename, layer_dir / filename)

    futures = [
        _prefetch_pool.submit(_fetch, layer.filename)
        for layer in config.layers
        if not (layer_dir / layer.filename).exists()
        and not (_TMP_LAYERS / model / layer.filename).exists()
    ]
    for f in futures:
        try:
            f.result()
        except Exception as exc:
            logger.warning("Prefetch error: %s", exc)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

VALID_MODELS = {"eva_ribelle", "essesse9", "ego", "experia"}


class ConfigureRequest(BaseModel):
    """Request body for POST /configure."""

    model: str = Field(..., description="Motorcycle model identifier.")
    layers: list[str] = Field(..., description="List of layer IDs to render.")
    format: Literal["jpeg", "png"] = Field("jpeg", description="Output image format.")
    quality: int = Field(85, ge=1, le=95, description="JPEG quality (ignored for PNG).")

    @field_validator("model")
    @classmethod
    def model_must_be_valid(cls, v: str) -> str:
        if v not in VALID_MODELS:
            raise ValueError(f"Unknown model '{v}'. Valid: {sorted(VALID_MODELS)}")
        return v


class ValidateRequest(BaseModel):
    """Request body for POST /validate."""

    model: str
    layers: list[str]

    @field_validator("model")
    @classmethod
    def model_must_be_valid(cls, v: str) -> str:
        if v not in VALID_MODELS:
            raise ValueError(f"Unknown model '{v}'. Valid: {sorted(VALID_MODELS)}")
        return v


class LayerMeta(BaseModel):
    """Metadata for a single layer as stored in config.json."""

    id: str
    name: str
    filename: str
    z_index: int
    offset_x: int = 0
    offset_y: int = 0
    visible_by_default: bool
    always_visible: bool
    group: str


class ConfigRules(BaseModel):
    """Validation rules for a model configuration."""

    always_visible: list[str] = []
    mutually_exclusive: list[list[str]] = []
    dependencies: dict[str, list[str]] = {}
    # any_of_dependencies: if layer X is active, at least one of the listed
    # layers must also be active (OR semantics, unlike dependencies which is AND).
    any_of_dependencies: dict[str, list[str]] = {}
    # incompatibilities: if layer X is active, none of the listed layers may
    # be active simultaneously.
    incompatibilities: dict[str, list[str]] = {}


class ConfigSchema(BaseModel):
    """Full configuration schema as returned by GET /config/{model}."""

    model: str
    canvas: dict[str, int]
    layers: list[LayerMeta]
    groups: dict[str, list[str]]
    rules: ConfigRules


class ValidateResponse(BaseModel):
    valid: bool
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    compositor: str
    cache: str


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4)
def load_config(model: str) -> ConfigSchema:
    """
    Load and parse config.json for a model.
    Result is cached in-process (LRU) since configs change only on deployment.
    """
    config_path = settings.layer_path / model / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found for model '{model}': {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return ConfigSchema.model_validate(raw)


# ---------------------------------------------------------------------------
# Configuration validator
# ---------------------------------------------------------------------------


class ConfigValidator:
    """Validates a layer selection against a model's business rules."""

    def __init__(self, config: ConfigSchema) -> None:
        self._config = config
        self._valid_ids: set[str] = {layer.id for layer in config.layers}
        # "Required groups" are mutually_exclusive groups that contain at least
        # one visible_by_default layer (marked * in PSD). Exactly one from each
        # required group must always be active (e.g. suspension, wheels, seat).
        default_ids = {l.id for l in config.layers if l.visible_by_default}
        self._required_groups: list[list[str]] = [
            grp for grp in config.rules.mutually_exclusive
            if any(lid in default_ids for lid in grp)
        ]

    def validate(self, layer_ids: list[str]) -> tuple[bool, str | None]:
        """
        Check a layer selection for rule violations.

        Returns
        -------
        (True, None) if valid, or (False, error_message) otherwise.
        """
        requested = set(layer_ids)
        rules = self._config.rules

        # All requested IDs must exist
        unknown = requested - self._valid_ids
        if unknown:
            return False, f"Unknown layer IDs: {sorted(unknown)}"

        # Always-visible layers must be present
        missing_required = set(rules.always_visible) - requested
        if missing_required:
            return False, f"Required layers missing: {sorted(missing_required)}"

        # Required groups — exactly one must be active (suspension, wheels, seat, etc.)
        for group_members in self._required_groups:
            active = [lid for lid in group_members if lid in requested]
            if len(active) == 0:
                return False, (
                    f"One layer required from group {group_members}; none selected."
                )

        # Mutually exclusive groups — at most one per group may be active
        for group_members in rules.mutually_exclusive:
            active = [lid for lid in group_members if lid in requested]
            if len(active) > 1:
                return False, (
                    f"Only one layer allowed from group {group_members}; "
                    f"got: {active}"
                )

        # AND-dependencies — if a layer is selected, ALL listed deps must be present
        for layer_id, deps in rules.dependencies.items():
            if layer_id in requested:
                missing_deps = set(deps) - requested
                if missing_deps:
                    return False, (
                        f"Layer '{layer_id}' requires: {sorted(missing_deps)}"
                    )

        # OR-dependencies — if a layer is selected, AT LEAST ONE of the listed
        # options must be present (e.g. rider seat needs matching passenger seat OR cover)
        for layer_id, options in rules.any_of_dependencies.items():
            if layer_id in requested:
                if not any(opt in requested for opt in options):
                    return False, (
                        f"Layer '{layer_id}' requires at least one of: {sorted(options)}"
                    )

        # Incompatibilities — if layer X is active, listed layers must NOT be active
        for layer_id, incompatible in rules.incompatibilities.items():
            if layer_id in requested:
                conflicts = [lid for lid in incompatible if lid in requested]
                if conflicts:
                    return False, (
                        f"Layer '{layer_id}' is incompatible with: {conflicts}"
                    )

        return True, None


# ---------------------------------------------------------------------------
# Image compositor
# ---------------------------------------------------------------------------


class ImageCompositor:
    """Composites selected PSD layers into a single image using Pillow."""

    def __init__(self, model: str, config: ConfigSchema) -> None:
        self._model = model
        self._config = config
        self._layer_dir = settings.layer_path / model
        self._layers_by_id: dict[str, LayerMeta] = {
            layer.id: layer for layer in config.layers
        }

    def composite(
        self,
        layer_ids: list[str],
        fmt: Literal["jpeg", "png"] = "jpeg",
        quality: int = 85,
    ) -> bytes:
        """
        Composite the requested layers and return the encoded image bytes.

        Parameters
        ----------
        layer_ids:
            Ordered list of layer IDs to render (bottom-to-top by z_index).
        fmt:
            Output format — 'jpeg' or 'png'.
        quality:
            JPEG quality level (1-95).
        """
        canvas_w = self._config.canvas["width"]
        canvas_h = self._config.canvas["height"]

        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        requested_set = set(layer_ids)

        # psd-tools iterates layers bottom-to-top in the PS layers panel,
        # so z_index=0 is the TOP layer (accessories) and the highest z_index
        # is the BACKGROUND. We must composite highest z first (background),
        # then build upward to lowest z (top accessories).
        ordered = [
            meta
            for meta in sorted(self._layers_by_id.values(), key=lambda l: l.z_index, reverse=True)
            if meta.id in requested_set
        ]

        for meta in ordered:
            png_path = _resolve_layer_path(self._model, meta.filename, self._layer_dir / meta.filename)
            if not png_path.exists():
                logger.warning("Layer file missing: %s — skipped.", png_path)
                continue
            try:
                layer_img = Image.open(png_path).convert("RGBA")
                # Place layer at its original PSD canvas offset, not (0, 0)
                canvas.alpha_composite(layer_img, dest=(meta.offset_x, meta.offset_y))
            except Exception as exc:
                logger.error("Failed to composite layer '%s': %s", meta.id, exc)

        # Encode output
        buf = io.BytesIO()
        if fmt == "jpeg":
            rgb = Image.new("RGB", canvas.size, (255, 255, 255))
            rgb.paste(canvas, mask=canvas.split()[3])
            rgb.save(buf, format="JPEG", quality=quality, optimize=True)
            media_type = "image/jpeg"
        else:
            canvas.save(buf, format="PNG", optimize=True)
            media_type = "image/png"

        logger.info(
            "Composited %d layers for model '%s' → %s (%d bytes)",
            len(ordered),
            self._model,
            fmt,
            buf.tell(),
        )
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Cache layer (in-memory fallback; Redis used when available)
# ---------------------------------------------------------------------------


class ImageCache:
    """Simple in-memory image cache with optional Redis backing."""

    def __init__(self) -> None:
        self._mem: dict[str, tuple[bytes, float]] = {}
        self._redis: Any = None
        self._ttl = settings.cache_ttl
        self._backend = "memory"

        if settings.redis_url:
            try:
                import redis

                client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
                client.ping()
                self._redis = client
                self._backend = "redis"
                logger.info("Redis cache connected: %s", settings.redis_url)
            except Exception as exc:
                logger.warning("Redis unavailable — falling back to in-memory cache: %s", exc)

    @staticmethod
    def make_key(model: str, layers: list[str], fmt: str) -> str:
        payload = f"{model}:{':'.join(sorted(layers))}:{fmt}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> bytes | None:
        if self._redis is not None:
            try:
                value = self._redis.get(key)
                if value:
                    return bytes(value)
            except Exception as exc:
                logger.warning("Redis GET error: %s", exc)

        entry = self._mem.get(key)
        if entry and (time.time() - entry[1]) < self._ttl:
            return entry[0]
        return None

    def set(self, key: str, value: bytes) -> None:
        if self._redis is not None:
            try:
                self._redis.setex(key, self._ttl, value)
                return
            except Exception as exc:
                logger.warning("Redis SET error: %s", exc)

        self._mem[key] = (value, time.time())

    @property
    def backend(self) -> str:
        return self._backend


_cache = ImageCache()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Energica Compositor Service",
    description="Composites PSD layers into preview images for the Energica Configurator.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    """Service health check."""
    try:
        _ = settings.layer_path.exists()
        compositor_status = "ok"
    except Exception:
        compositor_status = "error"

    return HealthResponse(
        status="ok",
        compositor=compositor_status,
        cache=_cache.backend,
    )


@app.get("/config/{model}", response_model=ConfigSchema, tags=["config"])
async def get_config(model: str, background_tasks: BackgroundTasks) -> ConfigSchema:
    """Return the full layer configuration schema for a model."""
    if model not in VALID_MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model}")
    try:
        config = load_config(model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to load config for model '%s': %s", model, exc)
        raise HTTPException(status_code=500, detail="Failed to load model configuration.") from exc
    # Pre-download all layer PNGs in background so /configure is fast
    background_tasks.add_task(_prefetch_model_layers, model, config)
    return config


@app.post("/validate", response_model=ValidateResponse, tags=["config"])
async def validate(request: ValidateRequest) -> ValidateResponse:
    """Validate a layer selection without rendering an image."""
    try:
        config = load_config(request.model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    validator = ConfigValidator(config)
    valid, error = validator.validate(request.layers)
    return ValidateResponse(valid=valid, error=error)


@app.post("/configure", tags=["render"])
async def configure(request: ConfigureRequest, background_tasks: BackgroundTasks) -> Response:
    """
    Composite selected layers and return the result as an image.

    - Cache hit: <500ms
    - Cache miss (fresh composite): <2s
    """
    # Load model config
    try:
        config = load_config(request.model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Validate layer selection
    validator = ConfigValidator(config)
    valid, error = validator.validate(request.layers)
    if not valid:
        raise HTTPException(status_code=422, detail=error)

    cache_key = ImageCache.make_key(request.model, request.layers, request.format)
    media_type = "image/jpeg" if request.format == "jpeg" else "image/png"

    cache_headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "ETag": cache_key[:16],
    }

    # Try cache first
    cached = _cache.get(cache_key)
    if cached:
        logger.debug("Cache hit: %s", cache_key[:12])
        return Response(content=cached, media_type=media_type, headers=cache_headers)

    # Composite
    try:
        compositor = ImageCompositor(request.model, config)
        image_bytes = compositor.composite(
            layer_ids=request.layers,
            fmt=request.format,
            quality=request.quality,
        )
    except Exception as exc:
        logger.exception("Compositing failed for model '%s': %s", request.model, exc)
        raise HTTPException(status_code=500, detail="Image compositing failed.") from exc

    # Store in cache asynchronously (non-blocking)
    background_tasks.add_task(_cache.set, cache_key, image_bytes)

    return Response(content=image_bytes, media_type=media_type, headers=cache_headers)
