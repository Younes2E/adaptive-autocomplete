"""Empreinte memoire et cout de construction : trie contre index SymSpell.

Les deux structures partent de la meme liste de mots, deja en memoire, et on ne
compte que ce que la structure ajoute :
  memoire   octets Python alloues par la construction et encore vivants a la
            fin (tracemalloc), donc ni l'interpreteur ni la liste de mots
  temps     construction seule, sans la lecture du fichier, mesuree dans une
            construction a part (tracemalloc ralentit les allocations)

    python benchmarks/bench_memory.py    # ecrit results/memory.csv
"""
import csv
import gc
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "benchmarks"))
from bench import load_words                     # noqa: E402
from symspell import build_delete_index          # noqa: E402
from trie import Trie                            # noqa: E402

SIZES = [10_000, 50_000, 100_000, 333_333]
RADII = [1, 2]


def build_trie(words):
    trie = Trie()
    for w, freq in words:
        trie.add(w, freq=freq)
    return trie


def measure(build):
    """(Go, secondes) : une construction chronometree, puis une sous tracemalloc."""
    gc.collect()
    t0 = time.perf_counter()
    built = build()
    secs = time.perf_counter() - t0
    del built
    gc.collect()
    tracemalloc.start()
    built = build()
    held = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    return held / 1024 ** 3, secs, built


def main():
    rows = []
    print(f"{'structure':>9} {'dico':>7} {'k':>2} | {'Go':>7} {'build s':>8} {'entrees':>12}")
    print("-" * 52)
    for size in SIZES:
        words = load_words(size)
        names = [w for w, _ in words]
        gb, secs, built = measure(lambda: build_trie(words))
        del built
        rows.append(["trie", size, "", round(gb, 4), round(secs, 3), ""])
        print(f"{'trie':>9} {size:>7} {'-':>2} | {gb:>7.3f} {secs:>8.2f} {'-':>12}", flush=True)
        for k in RADII:
            gb, secs, built = measure(lambda: build_delete_index(names, k, 3))
            entries = built[2]
            del built
            rows.append(["symspell", size, k, round(gb, 4), round(secs, 3), entries])
            print(f"{'symspell':>9} {size:>7} {k:>2} | {gb:>7.3f} {secs:>8.2f} {entries:>12,}",
                  flush=True)
    path = ROOT / "results" / "memory.csv"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["structure", "dict_size", "k", "index_gb", "build_s", "entries"])
        w.writerows(rows)
    print(f"  -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
