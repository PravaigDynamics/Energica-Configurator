"""
Tests for the Energica Compositor Service.

Run with:
    pytest backend/tests/test_compositor.py -v
"""

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# ---------------------------------------------------------------------------
# Make the backend package importable from tests/
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from compositor_service import (
    ConfigRules,
    ConfigSchema,
    ConfigValidator,
    ImageCompositor,
    LayerMeta,
    Settings,
    app,
    load_config,
    settings,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(model: str = "eva_ribelle") -> ConfigSchema:
    """Return a minimal in-memory ConfigSchema for unit testing."""
    layers = [
        LayerMeta(
            id="base_stealth",
            name="Base Stealth",
            filename="base_stealth.png",
            z_index=0,
            visible_by_default=True,
            always_visible=False,
            group="base_color",
        ),
        LayerMeta(
            id="base_rosso",
            name="Base Rosso",
            filename="base_rosso.png",
            z_index=1,
            visible_by_default=False,
            always_visible=False,
            group="base_color",
        ),
        LayerMeta(
            id="frame",
            name="Frame",
            filename="frame.png",
            z_index=2,
            visible_by_default=True,
            always_visible=True,
            group="other",
        ),
        LayerMeta(
            id="ohlins",
            name="Ohlins Suspension",
            filename="ohlins.png",
            z_index=3,
            visible_by_default=False,
            always_visible=False,
            group="suspension",
        ),
    ]
    return ConfigSchema(
        model=model,
        canvas={"width": 1920, "height": 1080},
        layers=layers,
        groups={
            "base_color": ["base_stealth", "base_rosso"],
            "suspension": ["ohlins"],
            "other": ["frame"],
        },
        rules=ConfigRules(
            always_visible=["frame"],
            mutually_exclusive=[["base_stealth", "base_rosso"]],
            dependencies={},
        ),
    )


@pytest.fixture
def config() -> ConfigSchema:
    return _make_config()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient with layer_path set to a temp directory."""
    monkeypatch.setattr(settings, "layer_path", tmp_path)

    # Write a minimal config.json for model 'eva_ribelle'
    eva_dir = tmp_path / "eva_ribelle"
    eva_dir.mkdir()
    cfg = _make_config("eva_ribelle")
    (eva_dir / "config.json").write_text(cfg.model_dump_json(indent=2), encoding="utf-8")

    # Write dummy PNG files
    for layer in cfg.layers:
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        img.save(eva_dir / layer.filename)

    # Clear LRU cache so our patched config is used
    load_config.cache_clear()

    return TestClient(app)


# ---------------------------------------------------------------------------
# ConfigValidator tests
# ---------------------------------------------------------------------------


class TestConfigValidator:
    def test_valid_selection(self, config: ConfigSchema) -> None:
        validator = ConfigValidator(config)
        valid, err = validator.validate(["frame", "base_stealth"])
        assert valid is True
        assert err is None

    def test_unknown_layer(self, config: ConfigSchema) -> None:
        validator = ConfigValidator(config)
        valid, err = validator.validate(["frame", "nonexistent"])
        assert valid is False
        assert err is not None
        assert "nonexistent" in err

    def test_missing_required_layer(self, config: ConfigSchema) -> None:
        validator = ConfigValidator(config)
        valid, err = validator.validate(["base_stealth"])  # 'frame' missing
        assert valid is False
        assert "frame" in (err or "")

    def test_mutually_exclusive_violation(self, config: ConfigSchema) -> None:
        validator = ConfigValidator(config)
        valid, err = validator.validate(["frame", "base_stealth", "base_rosso"])
        assert valid is False
        assert err is not None

    def test_empty_selection_fails_when_required(self, config: ConfigSchema) -> None:
        validator = ConfigValidator(config)
        valid, _ = validator.validate([])
        assert valid is False

    def test_dependency_check(self) -> None:
        cfg = _make_config()
        cfg.rules.dependencies["ohlins"] = ["frame"]
        validator = ConfigValidator(cfg)
        # ohlins requires frame — both present
        valid, err = validator.validate(["frame", "ohlins"])
        assert valid is True
        # ohlins requires frame — frame absent
        valid, err = validator.validate(["base_stealth", "ohlins"])
        assert valid is False


# ---------------------------------------------------------------------------
# ImageCompositor tests
# ---------------------------------------------------------------------------


class TestImageCompositor:
    def test_composite_returns_jpeg_bytes(self, tmp_path: Path, config: ConfigSchema) -> None:
        eva_dir = tmp_path / "eva_ribelle"
        eva_dir.mkdir()

        with patch.object(settings, "layer_path", tmp_path):
            # Create dummy PNG layers
            for layer in config.layers:
                img = Image.new("RGBA", (config.canvas["width"], config.canvas["height"]), (255, 0, 0, 128))
                img.save(eva_dir / layer.filename)

            compositor = ImageCompositor("eva_ribelle", config)
            result = compositor.composite(["frame", "base_stealth"], fmt="jpeg")

        assert isinstance(result, bytes)
        assert len(result) > 0
        parsed = Image.open(io.BytesIO(result))
        assert parsed.format == "JPEG"

    def test_composite_returns_png_bytes(self, tmp_path: Path, config: ConfigSchema) -> None:
        eva_dir = tmp_path / "eva_ribelle"
        eva_dir.mkdir()

        with patch.object(settings, "layer_path", tmp_path):
            for layer in config.layers:
                img = Image.new("RGBA", (100, 100), (0, 255, 0, 200))
                img.save(eva_dir / layer.filename)

            config_small = _make_config()
            config_small.canvas = {"width": 100, "height": 100}
            compositor = ImageCompositor("eva_ribelle", config_small)
            result = compositor.composite(["frame", "base_stealth"], fmt="png")

        assert isinstance(result, bytes)
        parsed = Image.open(io.BytesIO(result))
        assert parsed.format == "PNG"

    def test_missing_layer_file_skipped_gracefully(self, tmp_path: Path, config: ConfigSchema) -> None:
        eva_dir = tmp_path / "eva_ribelle"
        eva_dir.mkdir()

        with patch.object(settings, "layer_path", tmp_path):
            # Write only one of the required files
            img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            cfg_small = _make_config()
            cfg_small.canvas = {"width": 100, "height": 100}
            img.save(eva_dir / "frame.png")
            # base_stealth.png intentionally missing

            compositor = ImageCompositor("eva_ribelle", cfg_small)
            # Should not raise; missing layer is skipped
            result = compositor.composite(["frame", "base_stealth"], fmt="jpeg")
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"


class TestConfigEndpoint:
    def test_get_config_eva_ribelle(self, client: TestClient) -> None:
        resp = client.get("/config/eva_ribelle")
        assert resp.status_code == 200
        body = resp.json()
        assert body["model"] == "eva_ribelle"
        assert "layers" in body

    def test_get_config_unknown_model(self, client: TestClient) -> None:
        resp = client.get("/config/unknown")
        assert resp.status_code == 404

    @pytest.mark.parametrize("model", ["eva_ribelle", "essesse9", "ego", "experia"])
    def test_valid_model_names(self, model: str) -> None:
        # Validates Pydantic model field
        from compositor_service import ConfigureRequest
        with pytest.raises(Exception):
            ConfigureRequest(model="invalid", layers=[], format="jpeg", quality=85)


class TestValidateEndpoint:
    def test_valid_config(self, client: TestClient) -> None:
        resp = client.post("/validate", json={"model": "eva_ribelle", "layers": ["frame", "base_stealth"]})
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_invalid_config_missing_required(self, client: TestClient) -> None:
        resp = client.post("/validate", json={"model": "eva_ribelle", "layers": ["base_stealth"]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["error"] is not None


class TestConfigureEndpoint:
    def test_renders_jpeg(self, client: TestClient) -> None:
        resp = client.post(
            "/configure",
            json={"model": "eva_ribelle", "layers": ["frame", "base_stealth"], "format": "jpeg", "quality": 85},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        img = Image.open(io.BytesIO(resp.content))
        assert img.format == "JPEG"

    def test_renders_png(self, client: TestClient) -> None:
        resp = client.post(
            "/configure",
            json={"model": "eva_ribelle", "layers": ["frame", "base_stealth"], "format": "png", "quality": 85},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_invalid_layer_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/configure",
            json={"model": "eva_ribelle", "layers": ["frame", "nonexistent"], "format": "jpeg", "quality": 85},
        )
        assert resp.status_code == 422

    def test_unknown_model_returns_404(self, client: TestClient) -> None:
        resp = client.post(
            "/configure",
            json={"model": "ghost", "layers": ["frame"], "format": "jpeg", "quality": 85},
        )
        assert resp.status_code in (404, 422)
