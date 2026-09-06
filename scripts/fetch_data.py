"""Download Norvig's spelling-error test sets.

curl -L is required: the bare URLs return 301 and a plain fetch would silently
save the redirect HTML page instead of the data.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data" / "test"

FILES = {
    "spell-errors.txt": "https://norvig.com/ngrams/spell-errors.txt",
    "spell-testset1.txt": "https://norvig.com/spell-testset1.txt",
    "spell-testset2.txt": "https://norvig.com/spell-testset2.txt",
}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    ok = True
    for name, url in FILES.items():
        target = DEST / name
        if target.exists() and target.stat().st_size > 1000:
            print(f"  {name}: already present ({target.stat().st_size} bytes)")
            continue
        print(f"  fetching {name} ...", flush=True)
        r = subprocess.run(["curl", "-sL", "-m", "120", "-o", str(target), url])
        if r.returncode != 0 or not target.exists():
            print(f"    FAILED ({url})")
            ok = False
            continue
        head = target.read_text(encoding="utf-8", errors="ignore")[:200]
        if "<!DOCTYPE" in head or "<html" in head:
            print("    FAILED: got HTML, not data (redirect not followed)")
            ok = False
            continue
        print(f"    ok, {sum(1 for _ in target.open(encoding='utf-8', errors='ignore'))} lines")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
