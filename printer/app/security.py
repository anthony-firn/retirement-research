"""Single-household server access. Multi-user hosting needs separate identities and storage."""
import secrets
from urllib.parse import urlsplit
from fastapi.responses import JSONResponse

def origin(url):
    try:
        p = urlsplit(url)
        return p.scheme, p.hostname, p.port
    except ValueError:
        return None

def guard(token="", allowed_origins=()):
    trusted = set(allowed_origins) if token else set()
    async def access(request, call_next):
        if not request.url.path.startswith("/api/") or request.method == "OPTIONS":
            return await call_next(request)
        if token:
            supplied = request.headers.get("authorization", "")
            if not secrets.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
                return JSONResponse({"detail": "Connect with your server access key."}, status_code=401,
                                    headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"})
        if request.method == "POST" and request.url.path.startswith("/api/ops/"):
            source = request.headers.get("origin") or request.headers.get("referer") or ""
            if source and source not in trusted and origin(source) != origin(str(request.url)):
                return JSONResponse({"detail": "Not allowed."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response
    return access
