"""
Energica PSD Extraction Utility

Extracts all visible layers from a PSD file as individual PNG files
and generates a config.json for the compositor service.

Usage:
    python extract_psd.py <psd_path> --model <model_name>

Example:
    python extract_psd.py /path/to/EVA.psd --model eva
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.psd_image import PSDImage as PSDImageType
from psd_tools.api.layers import Layer, Group as GroupLayer

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("extract_psd")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LAYER_GROUPS: dict[str, list[str]] = {
    "base_color": ["stealth", "rosso", "tricolore", "ribelle", "color", "bormio", "riviera",
                   "sunrise", "titanium", "metal black", "white flame", "base-"],
    "suspension": ["ohlins", "suspension", "fork", "shock", "standard suspension"],
    "wheels": ["wheel", "rim", "spoke", "forged aluminium", "carbon fiber wheel",
               "red stripe cast", "standard cast"],
    "carbon_parts": ["carbon", "mudguard", "battery_cover", "tank_rib", "undertail",
                     "bellypan carbon"],
    "optional_upgrades": ["windscreen", "splash", "bag", "upgrade", "kit ergal",
                          "handguard", "central stand", "seat kit", "rs version",
                          "sticker", "rs sport", "corsaclienti", "passenger seat",
                          "rider seat", "bellypan"],
}

# Only truly structural layers are always visible (not color layers).
# The # prefix in PSD names marks the default color selection, not a structural layer.
ALWAYS_VISIBLE_KEYWORDS: list[str] = ["frame black", "background"]

MUTUALLY_EXCLUSIVE_GROUPS: list[str] = ["base_color", "suspension", "wheels"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_id(name: str) -> str:
    """Convert a layer name to a clean, normalized ID (lowercase, underscores)."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s_-]", "", name)
    cleaned = re.sub(r"[\s-]+", "_", cleaned.strip())
    return cleaned.lower()


def classify_layer(name: str) -> str:
    """
    Return the group key that best matches a layer name.

    PSD naming conventions used by Energica:
      #XX-NN  = default base color layer (group: base_color)
      *XX-NN  = default option within an exclusive group
      XX-NN   = non-default option
    """
    stripped = name.lstrip("#* ").lower()
    # # prefix always signals a base color
    if name.strip().startswith("#"):
        return "base_color"
    for group, keywords in LAYER_GROUPS.items():
        if any(kw in stripped for kw in keywords):
            return group
    return "optional_upgrades"


def is_always_visible(name: str) -> bool:
    """
    Return True only for structural layers that must always be rendered.
    Layers with a # prefix (default color variants) are NOT always-visible —
    they are selectable options within the base_color exclusive group.
    """
    stripped = name.lstrip("#* ")
    lower = stripped.lower()
    return any(kw in lower for kw in ALWAYS_VISIBLE_KEYWORDS)


def flatten_layers(psd: PSDImageType) -> list[Layer]:
    """Recursively flatten all leaf layers from the PSD tree."""
    result: list[Layer] = []

    def _walk(node: Layer | PSDImageType) -> None:
        if hasattr(node, "__iter__"):
            for child in node:
                _walk(child)
        if isinstance(node, GroupLayer):
            for child in node:
                _walk(child)
        elif not isinstance(node, (PSDImage,)):
            result.append(node)

    for layer in psd:
        if isinstance(layer, GroupLayer):
            for child in layer:
                _walk(child)
        else:
            result.append(layer)

    return result


# ---------------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------------


def extract_layer_png(layer: Layer, output_dir: Path, layer_id: str) -> Path | None:
    """
    Extract a single layer to a PNG file and return the output path.

    Uses topil() (raw pixel data) so that hidden layers are still captured
    correctly. Falls back to composite() for layers with no direct pixel data
    (e.g. smart objects, fill layers).
    """
    try:
        pil_image: Image.Image | None = None

        # topil() reads the stored pixels ignoring layer visibility.
        # This is critical: many variant layers (colours, frame) are hidden
        # by default in the PSD but contain real pixel data.
        try:
            pil_image = layer.topil()
        except Exception:
            pass

        # Fallback for smart-object / vector layers that have no raw pixels
        if pil_image is None:
            try:
                pil_image = layer.composite()
            except Exception:
                pass

        if pil_image is None:
            logger.warning("Layer '%s' produced no image — skipped.", layer.name)
            return None

        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")

        # Skip fully-transparent images (nothing to render)
        import numpy as _np
        if _np.array(pil_image)[:, :, 3].max() == 0:
            logger.warning("Layer '%s' is fully transparent — skipped.", layer.name)
            return None

        out_path = output_dir / f"{layer_id}.png"
        pil_image.save(out_path, format="PNG", optimize=True)
        logger.info("Saved layer '%s' → %s (%dx%d)", layer.name, out_path.name, *pil_image.size)
        return out_path
    except Exception as exc:
        logger.error("Failed to extract layer '%s': %s", layer.name, exc)
        return None


def build_config(
    model: str,
    canvas_size: tuple[int, int],
    layer_records: list[dict],
) -> dict:
    """
    Build the full config.json structure from extracted layer metadata.

    Parameters
    ----------
    model:
        Normalized model name (e.g. 'eva').
    canvas_size:
        (width, height) of the PSD canvas.
    layer_records:
        List of dicts, each describing one extracted layer.
    """
    groups: dict[str, list[str]] = {g: [] for g in LAYER_GROUPS}
    groups["other"] = []

    always_visible: list[str] = []
    mutually_exclusive: list[list[str]] = []

    for rec in layer_records:
        group = rec["group"]
        groups.setdefault(group, []).append(rec["id"])
        if rec["always_visible"]:
            always_visible.append(rec["id"])

    for group_key in MUTUALLY_EXCLUSIVE_GROUPS:
        members = groups.get(group_key, [])
        if len(members) > 1:
            mutually_exclusive.append(members)

    return {
        "model": model,
        "canvas": {"width": canvas_size[0], "height": canvas_size[1]},
        "layers": layer_records,
        "groups": {k: v for k, v in groups.items() if v},
        "rules": {
            "always_visible": always_visible,
            "mutually_exclusive": mutually_exclusive,
            "dependencies": {},
        },
    }


def extract_psd(psd_path: Path, model: str, output_base: Path) -> Path:
    """
    Extract all visible layers from a PSD and write PNG files + config.json.

    Parameters
    ----------
    psd_path:
        Absolute path to the source PSD file.
    model:
        Short model identifier (eva / essesse9 / ego / ribelle).
    output_base:
        Root output directory; a sub-directory named ``model`` will be created.

    Returns
    -------
    Path
        Path to the generated config.json.
    """
    if not psd_path.exists():
        raise FileNotFoundError(f"PSD not found: {psd_path}")

    output_dir = output_base / model
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Opening PSD: %s", psd_path)
    psd: PSDImage = PSDImage.open(str(psd_path))
    canvas_size = (psd.width, psd.height)
    logger.info("Canvas: %dx%d — total layers: %d", *canvas_size, len(list(psd.descendants())))

    layer_records: list[dict] = []
    seen_ids: dict[str, int] = {}
    z_index = 0

    # Iterate in PSD top-to-bottom order (highest z first); reverse for bottom-up compositing
    all_layers = list(psd.descendants())
    all_layers.reverse()  # bottom layer first

    for layer in all_layers:
        if isinstance(layer, GroupLayer):
            continue  # skip group nodes; we want leaf layers only

        raw_name: str = layer.name or f"layer_{z_index}"
        layer_id = normalize_id(raw_name)

        # Deduplicate IDs
        if layer_id in seen_ids:
            seen_ids[layer_id] += 1
            layer_id = f"{layer_id}_{seen_ids[layer_id]}"
        else:
            seen_ids[layer_id] = 0

        visible_default: bool = layer.is_visible()
        always_vis: bool = is_always_visible(raw_name)
        group: str = classify_layer(raw_name)

        out_path = extract_layer_png(layer, output_dir, layer_id)
        if out_path is None:
            z_index += 1
            continue

        # Store the layer's position within the canvas so the compositor
        # can place it at the correct offset rather than always at (0, 0).
        offset_x: int = int(layer.left) if hasattr(layer, "left") else 0
        offset_y: int = int(layer.top) if hasattr(layer, "top") else 0

        layer_records.append(
            {
                "id": layer_id,
                "name": raw_name,
                "filename": out_path.name,
                "z_index": z_index,
                "offset_x": offset_x,
                "offset_y": offset_y,
                "visible_by_default": visible_default,
                "always_visible": always_vis,
                "group": group,
            }
        )
        z_index += 1

    config = build_config(model, canvas_size, layer_records)
    config_path = output_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    logger.info("Config written: %s (%d layers)", config_path, len(layer_records))
    return config_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract PSD layers for the Energica Configurator."
    )
    parser.add_argument("psd_path", type=Path, help="Absolute path to the PSD file.")
    parser.add_argument(
        "--model",
        required=True,
        choices=["eva_ribelle", "essesse9", "ego", "experia"],
        help="Model identifier.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "layers",
        help="Base output directory (default: ./layers).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point; returns an exit code."""
    args = parse_args(argv)
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        config_path = extract_psd(
            psd_path=args.psd_path.resolve(),
            model=args.model,
            output_base=args.output.resolve(),
        )
        logger.info("Extraction complete. Config: %s", config_path)
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.exception("Unexpected error during extraction: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
