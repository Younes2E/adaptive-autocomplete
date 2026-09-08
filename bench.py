"""get_noise (DP sur Trie) contre baseline naive, en trois sections :

  1. CORRECTION      get_noise == force brute == baseline, sinon on s'arrete
  2. RAPPEL/PRECISION sur les fautes reelles de spell-testset1 (Norvig)
  3. TEMPS CPU        latence + travail effectue, par taille de dico x k x |q|

Metriques de la section 3 :
  noeuds     noeuds du Trie examines par get_noise -- independant du materiel
  generes    chaines enumerees par la baseline avant tout lookup -- idem
  ms         latence mediane sur `repeats` executions apres un warmup

Usage :
  python bench.py                             # tout, grille complete
  python bench.py --sizes 10000 --pairs 20    # rapide
  python bench.py --max-depth -1              # completions sans limite
  python bench.py > results/bench.txt         # garder la sortie
"""
import argparse
import gc
import platform
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from trie import Trie                                       # noqa: E402
from utils import osa_row                                   # noqa: E402
from baseline import build_prefix_index, naive_candidates   # noqa: E402

DICT = ROOT / "data" / "dict" / "en_freq.txt"               # voir data/SOURCES.md
TESTSET = ROOT / "data" / "test" / "spell-testset1.txt"
SIZES = [10_000, 50_000, 100_000, 333_333]
PREFIX_LENGTHS = [3, 4, 5, 6, 7]
RADII = [1, 2]
BASELINE_MAX = 100_000        # au-dela, l'index prefixe ne tient plus en memoire
ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def load(size):
    """(Trie, liste de mots) pour les `size` mots les plus frequents.
    en_freq.txt est trie par frequence decroissante : on prend les premieres lignes."""
    words = []
    with open(DICT, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                words.append((parts[0].lower(), int(parts[1])))
            if len(words) >= size:
                break
    trie = Trie()
    for w, freq in words:
        trie.add(w, freq=freq)
    return trie, [w for w, _ in words]


def load_testset(path):
    """'correct: faute1 faute2' -> [(faute, correct)]. spell-errors.txt utilise
    des virgules et des suffixes *N ; les deux formats sont geres."""
    pairs = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if ":" not in line:
                continue
            right, wrongs = line.split(":", 1)
            right = right.strip().lower()
            for tok in wrongs.replace(",", " ").split():
                tok = tok.split("*")[0].lower()
                if tok.isalpha() and right.isalpha():
                    pairs.append((tok, right))
    return pairs


def make_queries(words, length, n, seed=42):
    """n requetes de `length` caracteres : moitie prefixes propres, moitie avec
    une faute (substitution ou transposition) pour exercer le rayon k."""
    rng = random.Random(seed + length)
    pool = [w for w in words if len(w) >= length]
    out = []
    for idx, w in enumerate(rng.sample(pool, min(n, len(pool)))):
        p = w[:length]
        if idx % 2 == 0:
            out.append(p)
        elif idx % 4 == 1:
            i = rng.randrange(length - 1)
            out.append(p[:i] + p[i + 1] + p[i] + p[i + 2:])        # transposition
        else:
            i = rng.randrange(length)
            out.append(p[:i] + rng.choice(ALPHABET) + p[i + 1:])  # substitution
    return out


def reference(query, words, k, max_depth):
    """Verite terrain par force brute, volontairement lente :
    on garde w si UN prefixe de w est a distance <= k de la requete."""
    max_len = None if max_depth is None else len(query) + max_depth
    return {w for w in words
            if (max_len is None or len(w) <= max_len)
            and min(osa_row(query, w)) <= k}


# ------------------------------------------------------------ 1. correction --

def test_correctness(max_depth):
    """get_noise == baseline == force brute, sur un dico de 20k mots."""
    print("=== 1. CORRECTION (dico 20k) ===")
    trie, words = load(20_000)
    index = build_prefix_index(words)

    # Cas nommes : ceux qui ont ete faux un jour.
    t = Trie()
    for w in ["the", "then", "car", "care", "cat", "access", "act"]:
        t.add(w)
    assert "the" in {r[0] for r in t.get_noise("hte", 1)}, "hte -> the (transposition)"
    assert "car" in {r[0] for r in t.get_noise("acr", 1)}, "acr -> car (transposition)"
    assert {"access", "act"} <= {r[0] for r in t.get_noise("cra", 2, None)}, "cra -> access, act"
    print("  cas nommes            OK")

    # Etiquettes du canal : op vaut None ssi la requete est un prefixe exact.
    for q in ["the", "car", "ca"]:
        for w, op, *_ in t.get_noise(q, 1):
            assert (op is None) == w.startswith(q), f"label {q}->{w}: {op}"
    print("  etiquettes du canal   OK")

    # Egalite d'ensembles contre la force brute et contre la baseline.
    n_checked = 0
    for L in PREFIX_LENGTHS:
        for k in RADII:
            for q in make_queries(words, L, 4):
                got = {r[0] for r in trie.get_noise(q, k, max_depth)}
                ref = reference(q, words, k, max_depth)
                base, _ = naive_candidates(q, index, k, max_depth)
                assert got == ref, (f"get_noise != force brute : {q!r} k={k}\n"
                                    f"  en trop  : {sorted(got - ref)[:5]}\n"
                                    f"  manquant : {sorted(ref - got)[:5]}")
                assert got == base, f"get_noise != baseline : {q!r} k={k}"
                n_checked += 1
    print(f"  egalite d'ensembles   OK ({n_checked} requetes, k=1 et k=2)")
    print("=== CORRECT ===\n")


# ----------------------------------------------------- 2. rappel/precision --

def quality(size, n_pairs, max_depth):
    """Rappel et precision sur des fautes reelles.

    Pour chaque (faute, mot voulu) de spell-testset1, la requete est le prefixe
    de la faute de longueur |q|, ou la faute entiere (ligne 'mot').
      rappel    = le mot voulu est dans les candidats
      precision = 1 / |candidats| quand il y est (un seul mot est pertinent)
    La baseline est evaluee sur les memes paires : les deux colonnes doivent
    etre identiques, c'est la preuve que le gain de vitesse ne coute rien.
    """
    print(f"=== 2. RAPPEL / PRECISION (spell-testset1, dico {size}, {n_pairs} paires) ===")
    trie, words = load(size)
    vocab = set(words)
    index = build_prefix_index(words)
    pairs = [(w, r) for w, r in load_testset(TESTSET) if r in vocab][:n_pairs]
    hdr = (f"{'|q|':>4} {'k':>2} {'n':>4} | {'rappel':>7} {'precis.':>8} {'cands':>6} | "
           f"{'naive rappel':>12} {'naive prec.':>11}")
    print(hdr)
    print("-" * len(hdr))
    for L in PREFIX_LENGTHS + ["mot"]:
        for k in RADII:
            rec, prec, nrec, nprec, ncand = [], [], [], [], []
            for wrong, right in pairs:
                q = wrong if L == "mot" else wrong[:L]
                if (L != "mot" and len(wrong) < L) or k >= len(q):
                    continue
                got = {r[0] for r in trie.get_noise(q, k, max_depth)}
                base, _ = naive_candidates(q, index, k, max_depth)
                rec.append(right in got)
                prec.append(1 / len(got) if right in got else 0.0)
                nrec.append(right in base)
                nprec.append(1 / len(base) if right in base else 0.0)
                ncand.append(len(got))
            if rec:
                print(f"{str(L):>4} {k:>2} {len(rec):>4} | {statistics.mean(rec):>6.1%} "
                      f"{statistics.mean(prec):>7.1%} {statistics.median(ncand):>6.0f} | "
                      f"{statistics.mean(nrec):>11.1%} {statistics.mean(nprec):>10.1%}",
                      flush=True)
    print()


# ------------------------------------------------------------ 3. temps CPU --

def timeit(fn, repeats):
    """Mediane en ms. GC coupe pendant la mesure pour qu'une collecte ne tombe
    pas au milieu d'un echantillon."""
    fn()                                       # warmup
    gc.disable()
    try:
        samples = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            fn()
            samples.append(time.perf_counter() - t0)
    finally:
        gc.enable()
    return statistics.median(samples) * 1e3


def benchmark(sizes, n_queries, repeats, max_depth):
    print("=== 3. TEMPS CPU ===")
    print(f"  {platform.processor() or platform.machine()} / {platform.system()} / "
          f"Python {platform.python_version()} / {n_queries} requetes x {repeats} mesures")
    hdr = (f"{'dico':>7} {'|q|':>4} {'k':>2} | {'DP ms':>8} {'noeuds':>8} | "
           f"{'naive ms':>9} {'generes':>9} | {'gain':>6}")
    print(hdr)
    print("-" * len(hdr))
    for size in sizes:
        trie, words = load(size)
        index = build_prefix_index(words) if size <= BASELINE_MAX else None
        for L in PREFIX_LENGTHS:
            queries = make_queries(words, L, n_queries)
            for k in RADII:
                if k >= L:
                    continue
                dp_ms, dp_nodes, nv_ms, nv_gen = [], [], [], []
                for q in queries:
                    dp_ms.append(timeit(lambda: trie.get_noise(q, k, max_depth), repeats))
                    dp_nodes.append(trie.visited_nodes)
                    if index is not None:
                        nv_ms.append(timeit(lambda: naive_candidates(q, index, k, max_depth), repeats))
                        nv_gen.append(naive_candidates(q, index, k, max_depth)[1])
                dp, nodes = statistics.median(dp_ms), statistics.median(dp_nodes)
                if index is not None:
                    nv, gen = statistics.median(nv_ms), statistics.median(nv_gen)
                    print(f"{size:>7} {L:>4} {k:>2} | {dp:>8.2f} {nodes:>8.0f} | "
                          f"{nv:>9.2f} {gen:>9.0f} | {nv / dp:>5.0f}x", flush=True)
                else:
                    print(f"{size:>7} {L:>4} {k:>2} | {dp:>8.2f} {nodes:>8.0f} | "
                          f"{'OOM':>9} {'-':>9} | {'-':>6}", flush=True)
        del index
        gc.collect()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=SIZES)
    ap.add_argument("--queries", type=int, default=10, help="requetes par cellule (section 3)")
    ap.add_argument("--repeats", type=int, default=5, help="mesures par requete (section 3)")
    ap.add_argument("--pairs", type=int, default=60, help="paires du testset (section 2)")
    ap.add_argument("--quality-size", type=int, default=50_000, help="dico de la section 2")
    ap.add_argument("--max-depth", type=int, default=3,
                    help="caracteres autorises au-dela de la requete (-1 = sans limite)")
    ap.add_argument("--skip", nargs="*", default=[], choices=["test", "quality", "bench"])
    args = ap.parse_args()
    max_depth = None if args.max_depth < 0 else args.max_depth

    if "test" not in args.skip:
        test_correctness(max_depth)
    if "quality" not in args.skip:
        quality(args.quality_size, args.pairs, max_depth)
    if "bench" not in args.skip:
        benchmark(args.sizes, args.queries, args.repeats, max_depth)


if __name__ == "__main__":
    main()
