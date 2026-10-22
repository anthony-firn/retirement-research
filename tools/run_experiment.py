"""Run an isolated passive-improvement experiment; never promotes winners."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from research_snapshot import ROOT, snapshot

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--idea", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--paths", type=int, default=1000)
    p.add_argument("--fresh", type=int, default=2000)
    p.add_argument("--seed", required=True, type=int)
    a = p.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", a.name): p.error("Use a short lowercase experiment name, digits or hyphens.")
    if min(a.paths, a.fresh) < 1 or a.seed < 0: p.error("Paths and fresh paths must be positive; seed must be nonnegative.")
    inputs = snapshot()
    if inputs["missing"]: p.error("Missing generated inputs: " + ", ".join(inputs["missing"]))
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" and shutil.which("nvidia-smi"):
        q = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True)
        if q.returncode == 0 and any(float(t) >= 80 for t in q.stdout.splitlines()): p.error("GPU is at least 80C; cool before starting.")
    out = ROOT / "results" / "experiments" / a.name
    out.parent.mkdir(exist_ok=True)
    if out.exists(): p.error("Experiment directory already exists; choose a new name to preserve its evidence.")
    out.mkdir()
    reference = out / "reference.json"
    shutil.copyfile(ROOT / "results" / "improve_best.json", reference)
    env = {**os.environ, "IDEA": a.idea, "PATHS": str(a.paths), "FRESH": str(a.fresh), "THROTTLE": "1",
           "SEARCH_SEED": str(a.seed), "VALIDATION_SEED": str(a.seed + 10), "RESEARCH_OUT": str(out), "RESEARCH_BEST_FILE": str(reference)}
    # Inherited experiment selectors must not silently change the advertised experiment.
    for name in ("CONFIRM", "TRACKS", "CLIMB_PATHS", "CLIMB_SEED"): env.pop(name, None)
    command = [sys.executable, "printer/improve.py"]
    record = {"schema": 1, "idea": a.idea, "name": a.name, "paths": a.paths, "fresh": a.fresh,
              "search_seed": a.seed, "validation_seed": a.seed + 10, "throttle": 1,
              "command": ["python3", *command[1:]], "device_selection": os.environ.get("CUDA_VISIBLE_DEVICES", "automatic"),
              "smoke_only": min(a.paths, a.fresh) < 1000, "inputs": inputs, "status": "running"}
    manifest = out / "manifest.json"
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    print(f"Running {a.name}; output: {out.relative_to(ROOT)}", flush=True)
    try:
        with (out / "stdout.log").open("w") as stdout, (out / "stderr.log").open("w") as stderr:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        record.update(returncode=result.returncode, status="completed" if result.returncode == 0 else "failed")
    except BaseException:
        record["status"] = "interrupted"
        raise
    finally:
        record["finished_utc"] = dt.datetime.now(dt.UTC).isoformat()
        manifest.write_text(json.dumps(record, indent=2) + "\n")
    print(f"{record['status']}; no reference or app settings changed.")
    return result.returncode

if __name__ == "__main__": sys.exit(main())
