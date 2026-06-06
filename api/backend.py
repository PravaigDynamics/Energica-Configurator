import sys
import os
from pathlib import Path

_repo_root = Path(__file__).parent.parent
_backend_dir = _repo_root / "backend"

sys.path.insert(0, str(_backend_dir))
os.environ.setdefault("LAYER_PATH", str(_backend_dir / "layers"))

from starlette.types import ASGIApp, Receive, Scope, Send
from compositor_service import app as _fastapi_app

_PREFIX = "/api/backend"


class _StripPrefix:
    """Strip the Vercel route prefix before forwarding to FastAPI."""

    def __init__(self, app: ASGIApp, prefix: str) -> None:
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            path: str = scope.get("path", "")
            if path.startswith(self.prefix):
                stripped = path[len(self.prefix):] or "/"
                scope = {**scope, "path": stripped, "raw_path": stripped.encode()}
        await self.app(scope, receive, send)


app = _StripPrefix(_fastapi_app, _PREFIX)
