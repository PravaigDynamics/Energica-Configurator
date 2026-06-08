import sys
import os
import urllib.parse
from pathlib import Path

_repo_root = Path(__file__).parent.parent
_backend_dir = _repo_root / "backend"

sys.path.insert(0, str(_backend_dir))
os.environ.setdefault("LAYER_PATH", str(_backend_dir / "layers"))

from starlette.types import ASGIApp, Receive, Scope, Send
from compositor_service import app as _fastapi_app

_PREFIX = "/api/backend"


class _StripPrefix:
    """Route sub-paths to FastAPI by stripping the Vercel function prefix.

    Vercel rewrites change the ASGI scope path to the destination (/api/backend),
    but passes the original captured segments in the x-now-route-matches header.
    We read that header first; fall back to stripping the prefix from scope path.
    """

    def __init__(self, app: ASGIApp, prefix: str) -> None:
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            path = self._resolve_path(scope)
            scope = {**scope, "path": path, "raw_path": path.encode()}
        await self.app(scope, receive, send)

    def _resolve_path(self, scope: Scope) -> str:
        # Vercel sets x-now-route-matches when routing via a rewrite rule.
        # For source "/api/backend/:path*" it contains e.g. "path=config%2Feva_ribelle"
        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        route_matches = headers.get(b"x-now-route-matches", b"").decode()
        if route_matches:
            params = urllib.parse.parse_qs(route_matches)
            captured = params.get("path", [""])[0]
            if captured:
                return "/" + urllib.parse.unquote(captured)

        # Fallback: strip the function prefix from the scope path directly
        # (works when Vercel forwards the original path to the ASGI scope)
        raw: str = scope.get("path", "/")
        if raw.startswith(self.prefix):
            stripped = raw[len(self.prefix):]
            return stripped or "/"

        return raw or "/"


app = _StripPrefix(_fastapi_app, _PREFIX)
