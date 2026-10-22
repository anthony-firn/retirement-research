"""Fingerprint public research inputs without importing the simulator or reading private/."""
import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATA = ["lab/hist_long.json", "strategy/data_portfolios.json", "strategy/data_indicators.json",
        "strategy/data_portfolios_1972.json", "strategy/data_cpi_1972.json", "lab/clean_1972.json",
        "results/portfolios.json", "results/improve_best.json", "results/regress_baseline.json"]

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def snapshot():
    def git(*args): return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    sources = sorted(p.relative_to(ROOT).as_posix() for folder in ("engine", "printer", "strategy", "planner", "lab", "tools")
                     for p in (ROOT / folder).rglob("*.py") if "__pycache__" not in p.parts)
    files, missing = {}, []
    for name in sorted(set(sources + DATA)):
        p = ROOT / name
        if p.is_file(): files[name] = {"sha256": digest(p), "bytes": p.stat().st_size}
        else: missing.append(name)
    versions = {}
    for name in ("numpy", "torch", "fastapi", "uvicorn", "requests", "scipy"):
        try: versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: versions[name] = None
    return {"schema": 1, "created_utc": dt.datetime.now(dt.UTC).isoformat(), "commit": git("rev-parse", "HEAD"),
            "working_tree_dirty": bool(git("status", "--porcelain")), "python": platform.python_version(),
            "platform": {"system": platform.system(), "machine": platform.machine()}, "versions": versions,
            "files": files, "missing": missing,
            "note": "Hashes establish identity, not source rights, accuracy, or independent validation."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="-")
    args = parser.parse_args()
    content = json.dumps(snapshot(), indent=2) + "\n"
    if args.output == "-": print(content, end="")
    else: Path(args.output).write_text(content)
