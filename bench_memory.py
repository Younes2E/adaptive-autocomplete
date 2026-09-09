"""Empreinte memoire et cout de construction : trie contre index SymSpell.

Chaque mesure tourne dans un processus neuf (`maxrss` est un maximum
historique : mesurer plusieurs structures dans le meme processus donnerait le
maximum de la plus grosse, pas celui de chacune).

    python bench_memory.py          # ecrit results/memory.csv
"""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIZES = [10_000, 50_000, 100_000, 333_333]
RADII = [1, 2]

CHILD = r'''
import resource, sys, time
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from bench import load
size, which, k = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])

def gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 3)

t0 = time.perf_counter()
trie, words = load(size)
load_s, base = time.perf_counter() - t0, gb()

if which == "trie":
    print(f"{base:.4f},{load_s:.3f},0")
else:
    from symspell import build_delete_index
    t1 = time.perf_counter()
    _, _, entries = build_delete_index(words, k, 3)
    print(f"{gb() - base:.4f},{time.perf_counter() - t1:.3f},{entries}")
'''


def measure(size, which, k):
    out = subprocess.run([sys.executable, "-c", CHILD, str(size), which, str(k)],
                         cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        tail = out.stderr.strip().splitlines()[-1:] or ["echec"]
        print(f"  {which:>8} {size:>7} k={k} : ECHEC ({tail[0][:60]})")
        return None
    mem, secs, entries = out.stdout.strip().split(",")
    return float(mem), float(secs), int(entries)


def main():
    rows = []
    print(f"{'structure':>9} {'dico':>7} {'k':>2} | {'Go':>7} {'build s':>8} {'entrees':>12}")
    print("-" * 52)
    for size in SIZES:
        got = measure(size, "trie", 0)
        if got:
            rows.append(["trie", size, "", round(got[0], 4), got[1], ""])
            print(f"{'trie':>9} {size:>7} {'-':>2} | {got[0]:>7.3f} {got[1]:>8.2f} {'-':>12}")
        for k in RADII:
            got = measure(size, "symspell", k)
            if got:
                rows.append(["symspell", size, k, round(got[0], 4), got[1], got[2]])
                print(f"{'symspell':>9} {size:>7} {k:>2} | {got[0]:>7.3f} {got[1]:>8.2f} "
                      f"{got[2]:>12,}")
    path = ROOT / "results" / "memory.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["structure", "dict_size", "k", "index_gb", "build_s", "entries"])
        w.writerows(rows)
    print(f"  -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
