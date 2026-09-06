"""Single reproducibility entry point: regenerates every table and figure.

Order matters: the correctness gate runs BEFORE any benchmark and aborts the
run if it fails. Benchmarking a function that returns the wrong set measures
nothing.
"""
import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("PYTHONHASHSEED", "0")


def run(cmd, **kw):
    print(f"\n$ {' '.join(cmd)}", flush=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(cmd, cwd=ROOT, env=env, **kw).returncode


def manifest():
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "unknown"
    import numpy, pandas
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "git_sha": sha, "seed": 42,
        "python": platform.python_version(), "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "numpy": numpy.__version__, "pandas": pandas.__version__,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small grid, fast")
    ap.add_argument("--full", action="store_true", help="full grid + 333k gate")
    ap.add_argument("--skip-fetch", action="store_true")
    args = ap.parse_args()

    if not (ROOT / "data" / "matrices").is_dir():
        print("ERROR: run from the repository root (data/matrices not found)")
        return 2

    if not args.skip_fetch:
        if run([sys.executable, "scripts/fetch_data.py"]):
            print("WARNING: test-set download failed; evaluation will be skipped")

    env_extra = {"GATE_FULL": "1"} if args.full else {}
    os.environ.update(env_extra)
    if run([sys.executable, "tests/test_correctness.py"]):
        print("\nCORRECTNESS GATE FAILED -- stopping before any benchmark.")
        return 1
    print("\nGate passed; proceeding to measurements.")

    sizes = ["10000", "50000"] if args.quick else ["10000", "50000", "100000", "333333"]
    nq = "4" if args.quick else "8"
    run([sys.executable, "scripts/benchmark.py", "--sizes", *sizes,
         "--queries", nq, "--repeats", "3"])

    if (ROOT / "data" / "test" / "spell-testset1.txt").exists():
        run([sys.executable, "scripts/evaluate.py", "--testset", "testset1",
             "--dict-size", "50000", "--limit", "100" if args.quick else "250"])

    run([sys.executable, "scripts/make_figures.py"])

    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "manifest.json").write_text(json.dumps(manifest(), indent=2))
    print("\nmanifest:", json.dumps(manifest(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
