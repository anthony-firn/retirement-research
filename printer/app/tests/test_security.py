import sys
from pathlib import Path
import unittest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security import guard

def client(token="", origins=()):
    app = FastAPI()
    app.middleware("http")(guard(token, origins))
    @app.get("/api/ops/list")
    def read(): return {"ok": True}
    @app.post("/api/ops/commit")
    def write(): return {"ok": True}
    @app.get("/")
    def shell(): return {"public": True}
    if token:
        app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_methods=["GET", "POST"],
                           allow_headers=["Authorization", "Content-Type"])
    return TestClient(app)

class AccessTests(unittest.TestCase):
    def test_local_browser_origin_check(self):
        with client() as c:
            for source in ("https://evil.example", "http://testserver:9000", "http://testserver@evil.example", "null"):
                self.assertEqual(c.post("/api/ops/commit", headers={"Origin": source}).status_code, 403)
            self.assertEqual(c.post("/api/ops/commit", headers={"Origin": "http://testserver"}).status_code, 200)

    def test_key_protects_reads_and_writes(self):
        with client("test-key") as c:
            self.assertEqual(c.get("/").status_code, 200)
            for path, method in (("/api/ops/list", c.get), ("/api/ops/commit", c.post)):
                self.assertEqual(method(path).status_code, 401)
                self.assertEqual(method(path, headers={"Authorization": "Bearer wrong"}).status_code, 401)
                r = method(path, headers={"Authorization": "Bearer test-key"})
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.headers["cache-control"], "no-store")

    def test_native_origin_requires_key_and_explicit_permission(self):
        origin = "capacitor://localhost"
        with client("test-key", [origin]) as c:
            r = c.options("/api/ops/commit", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                     "Access-Control-Request-Headers": "Authorization,Content-Type"})
            self.assertEqual(r.status_code, 200)
            r = c.post("/api/ops/commit", headers={"Origin": origin})
            self.assertEqual(r.status_code, 401)
            self.assertEqual(r.headers["access-control-allow-origin"], origin)
            self.assertEqual(c.post("/api/ops/commit", headers={"Origin": origin, "Authorization": "Bearer test-key"}).status_code, 200)
        with client("", [origin]) as c:
            self.assertEqual(c.post("/api/ops/commit", headers={"Origin": origin}).status_code, 403)

if __name__ == "__main__": unittest.main()
