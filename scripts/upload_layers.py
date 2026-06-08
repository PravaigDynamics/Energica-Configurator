"""
Upload all extracted layer PNGs to Vercel Blob Storage (public access).

Usage:
    BLOB_READ_WRITE_TOKEN=<token> python scripts/upload_layers.py

The script prints the Blob base URL to set as BLOB_BASE_URL in Vercel
environment variables.

Run once locally after extracting PSDs. Re-run whenever layers are re-extracted.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

LAYERS_DIR = Path(__file__).parent.parent / "backend" / "layers"
BLOB_API = "https://blob.vercel-storage.com"
API_VERSION = "7"

token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
if not token:
    sys.exit("Error: BLOB_READ_WRITE_TOKEN environment variable is not set.\n"
             "Find it in Vercel Dashboard → Storage → your Blob store → .env.local tab.")

uploaded_urls: list[str] = []

for model_dir in sorted(LAYERS_DIR.iterdir()):
    if not model_dir.is_dir():
        continue
    model = model_dir.name
    png_files = sorted(model_dir.glob("*.png")) + sorted(model_dir.glob("*.PNG"))
    if not png_files:
        print(f"  [{model}] no PNG files found — skipping")
        continue
    print(f"\n[{model}] uploading {len(png_files)} file(s)...")
    for png_path in png_files:
        pathname = f"layers/{model}/{png_path.name}"
        url = f"{BLOB_API}/{urllib.parse.quote(pathname, safe='/')}"
        with open(png_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(url, data=data, method="PUT")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("x-api-version", API_VERSION)
        req.add_header("x-content-type", "image/png")
        req.add_header("x-access", "private")
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                blob_url: str = result["url"]
                uploaded_urls.append(blob_url)
                print(f"  ✓ {png_path.name}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            print(f"  ✗ {png_path.name} — HTTP {exc.code}: {body}", file=sys.stderr)

if not uploaded_urls:
    print("\nNo files uploaded.")
    sys.exit(0)

# Derive the store base URL from any uploaded URL
# Format: https://<store-id>.public.blob.vercel-storage.com/layers/...
sample = uploaded_urls[0]
base_url = sample.split("/layers/")[0]

print(f"\n{'='*60}")
print(f"Upload complete. {len(uploaded_urls)} file(s) uploaded.")
print(f"\nSet this in Vercel → Project → Settings → Environment Variables:")
print(f"\n  BLOB_BASE_URL = {base_url}\n")
