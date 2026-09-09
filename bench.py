"""get_noise (DP sur Trie) contre baseline naive, en trois sections :

  1. CORRECTION      le lemme, puis get_noise == force brute == baseline
  2. RAPPEL/PRECISION sur les fautes reelles (testset1 / testset2 / spell-errors)
  3. TEMPS CPU        latence + travail effectue, par taille de dico x k x |q|
  4. SYMSPELL        le meme, contre l'index de suppressions (Garbe 2012)

Metriques de la section 3 :
  noeuds     noeuds du Trie examines par get_noise -- independant du materiel
  generes    chaines enumerees par la baseline avant tout lookup -- idem
  ms         latence mediane sur `repeats` executions apres un warmup

Les tables sont aussi ecrites en CSV (results/quality.csv,
results/benchmark.csv) pour etre reprises telles quelles dans le papier.

Usage :
  python bench.py                             # tout, grille complete
  python bench.py --sizes 10000 --pairs 20    # rapide
  python bench.py --max-depth -1              # completions sans limite
  python bench.py > results/bench.txt         # garder la sortie
"""
import argparse
import csv
import functools
import gc
import platform
import random
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from trie import Trie                                       # noqa: E402
from utils import osa_row                                   # noqa: E402
from baseline import build_prefix_index, naive_candidates   # noqa: E402
from symspell import build_delete_index, symspell_candidates  # noqa: E402

DICT = ROOT / "data" / "dict" / "en_freq.txt"               # voir data/SOURCES.md
TESTSETS = {                                                # voir data/SOURCES.md
    "testset1": ROOT / "data" / "test" / "spell-testset1.txt",   # dev set (Norvig)
    "testset2": ROOT / "data" / "test" / "spell-testset2.txt",   # test set final
    "errors": ROOT / "data" / "test" / "spell-errors.txt",       # Wikipedia + Birkbeck
}
SIZES = [10_000, 50_000, 100_000, 333_333]
PREFIX_LENGTHS = [3, 4, 5, 6, 7]
RADII = [1, 2]
BASELINE_MAX = 100_000        # au-dela, l'index prefixe ne tient plus en memoire
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
RESULTS = ROOT / "results"


def write_csv(path, header, rows):
    """Ecrit la table telle qu'affichee, en machine-readable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  -> {path.relative_to(ROOT)}")


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


def osa_recursive(a, b):
    """OSA ecrite depuis la recurrence, en top-down memoise.

    Volontairement structuree autrement que `utils.osa_row` (recursion sur les
    indices, matrice implicite, pas de ligne roulante) : les deux ne partagent
    que la recurrence, pas le code. Sert uniquement de temoin dans le test du
    lemme ci-dessous ; trop lente pour le reste.
    """
    @functools.lru_cache(maxsize=None)
    def d(i, j):
        if i == 0:
            return j
        if j == 0:
            return i
        cost = 0 if a[i - 1] == b[j - 1] else 1
        best = min(d(i - 1, j) + 1, d(i, j - 1) + 1, d(i - 1, j - 1) + cost)
        if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
            best = min(best, d(i - 2, j - 2) + 1)
        return best
    return d(len(a), len(b))


def test_lemma(n_pairs=3000, seed=42):
    """Anti-circularite : la derniere ligne DP donne la distance a TOUS les prefixes.

    `get_noise` emet un sous-arbre quand la cellule n de sa ligne courante passe
    sous le rayon ; `reference` filtre sur `min(osa_row(...))`. Les deux reposent
    donc sur le meme lemme, et si ce lemme etait faux ils seraient faux a
    l'identique : l'egalite d'ensembles de `test_correctness` passerait a vide,
    sans rien prouver. On casse le cercle en recalculant chaque prefixe avec une
    implementation OSA independante.

    Ce que ce test etablit : `osa_row(a, b)[j] == OSA(a, b[:j])` pour tout j.
    Ce qu'il n'etablit pas : la recurrence OSA elle-meme, partagee par les deux
    implementations.
    """
    rng = random.Random(seed)
    small = ALPHABET[:6]        # alphabet reduit : plus de collisions et de
                                # transpositions possibles par tirage
    for _ in range(n_pairs):
        a = "".join(rng.choice(small) for _ in range(rng.randint(1, 7)))
        b = "".join(rng.choice(small) for _ in range(rng.randint(0, 9)))
        row = osa_row(a, b)
        assert len(row) == len(b) + 1, f"ligne de longueur {len(row)} pour |b|={len(b)}"
        for j in range(len(b) + 1):
            expected = osa_recursive(a, b[:j])
            assert row[j] == expected, (
                f"lemme faux : osa_row({a!r}, {b!r})[{j}] = {row[j]}, "
                f"or OSA({a!r}, {b[:j]!r}) = {expected}")


def wilson(successes, n, z=1.96):
    """Demi-largeur de l'intervalle de Wilson a 95 %, en points de pourcentage.

    Le rappel est une proportion mesuree sur un echantillon : sans intervalle,
    comparer 93.2 % (60 paires) a 54.4 % (300 paires) ne veut rien dire. Wilson
    plutot que l'approximation normale parce qu'il reste correct pres de 0 et
    de 1, ou plusieurs de nos cellules se trouvent.
    """
    if n == 0:
        return 0.0
    p = successes / n
    denom = 1 + z * z / n
    half = z / denom * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return half


def reference(query, words, k, max_depth):
    """Verite terrain par force brute, volontairement lente :
    on garde w si UN prefixe de w est a distance <= k de la requete."""
    max_len = None if max_depth is None else len(query) + max_depth
    return {w for w in words
            if (max_len is None or len(w) <= max_len)
            and min(osa_row(query, w)) <= k}


# ------------------------------------------------------------ 1. correction --

def test_scale(max_depth, sizes=(100_000, 333_333), n_queries=2):
    """Egalite d'ensembles echantillonnee aux tailles qu'on publie.

    Le gate principal tourne a 20k : rapide, exhaustif sur la grille. Mais les
    tables 1 a 3 chronometrent 100k et 333k, et rien n'y verifiait la
    correction. La force brute y coute des secondes par requete (osa_row sur
    chaque mot du dictionnaire), d'ou l'echantillon reduit et le flag dedie.
    """
    print("=== 1b. CORRECTION A L'ECHELLE ===")
    for size in sizes:
        trie, words = load(size)
        for L in (3, 5, 7):
            for q in make_queries(words, L, n_queries):
                for k in RADII:
                    if k >= L:
                        continue
                    got = {r[0] for r in trie.get_noise(q, k, max_depth)}
                    ref = reference(q, words, k, max_depth)
                    assert got == ref, (f"ecart a {size} mots : {q!r} k={k}\n"
                                        f"  en trop  : {sorted(got - ref)[:5]}\n"
                                        f"  manquant : {sorted(ref - got)[:5]}")
        print(f"  {size:>7} mots         OK ({n_queries} requetes x |q| in 3,5,7 x k in 1,2)",
              flush=True)
        del trie, words
        gc.collect()
    print("=== CORRECT A L'ECHELLE ===\n")


def test_correctness(max_depth):
    """Le lemme, puis get_noise == baseline == force brute, sur un dico de 20k mots."""
    print("=== 1. CORRECTION (dico 20k) ===")
    test_lemma()
    print("  lemme des prefixes    OK (3000 paires, temoin independant)")
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

def quality(size, n_pairs, max_depth, csv_path=None, testset="testset1"):
    """Rappel et precision sur des fautes reelles.

    Pour chaque (faute, mot voulu) de spell-testset1, la requete est le prefixe
    de la faute de longueur |q|, ou la faute entiere (ligne 'mot').
      rappel    = le mot voulu est dans les candidats
      precision = 1 / |candidats| quand il y est (un seul mot est pertinent)
    La baseline est evaluee sur les memes paires : les deux colonnes doivent
    etre identiques, c'est la preuve que le gain de vitesse ne coute rien.
    """
    path = TESTSETS[testset]
    print(f"=== 2. RAPPEL / PRECISION ({path.name}, dico {size}, {n_pairs} paires) ===")
    trie, words = load(size)
    vocab = set(words)
    index = build_prefix_index(words)
    # Echantillon deterministe : sur spell-errors (7841 lignes) prendre les
    # n premieres paires biaiserait vers le debut alphabetique du corpus.
    usable = [(w, r) for w, r in load_testset(path) if r in vocab]
    rng = random.Random(42)
    pairs = usable if len(usable) <= n_pairs else rng.sample(usable, n_pairs)
    print(f"  {len(usable)} paires exploitables, {len(pairs)} tirees")
    hdr = (f"{'|q|':>4} {'k':>2} {'n':>4} | {'rappel':>7} {'IC 95%':>9} {'precis.':>8} "
           f"{'cands':>6} | {'naive rappel':>12} {'naive prec.':>11}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
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
                ci = wilson(sum(rec), len(rec))
                rows.append([L, k, len(rec), round(statistics.mean(rec), 4),
                             round(ci, 4),
                             round(statistics.mean(prec), 4), statistics.median(ncand),
                             round(statistics.mean(nrec), 4), round(statistics.mean(nprec), 4)])
                print(f"{str(L):>4} {k:>2} {len(rec):>4} | {statistics.mean(rec):>6.1%} "
                      f"{'+/-' + format(ci, '.1%'):>9} "
                      f"{statistics.mean(prec):>7.1%} {statistics.median(ncand):>6.0f} | "
                      f"{statistics.mean(nrec):>11.1%} {statistics.mean(nprec):>10.1%}",
                      flush=True)
    if csv_path:
        write_csv(csv_path, ["prefix_len", "k", "n", "recall", "recall_ci95",
                             "precision", "median_candidates",
                             "naive_recall", "naive_precision"], rows)
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


def benchmark(sizes, n_queries, repeats, max_depth, csv_path=None):
    print("=== 3. TEMPS CPU ===")
    print(f"  {platform.processor() or platform.machine()} / {platform.system()} / "
          f"Python {platform.python_version()} / {n_queries} requetes x {repeats} mesures")
    hdr = (f"{'dico':>7} {'|q|':>4} {'k':>2} | {'DP ms':>8} {'noeuds':>8} | "
           f"{'naive ms':>9} {'generes':>9} | {'gain':>6}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
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
                    rows.append([size, L, k, round(dp, 3), int(nodes),
                                 round(nv, 3), int(gen), round(nv / dp, 1)])
                    print(f"{size:>7} {L:>4} {k:>2} | {dp:>8.2f} {nodes:>8.0f} | "
                          f"{nv:>9.2f} {gen:>9.0f} | {nv / dp:>5.0f}x", flush=True)
                else:
                    rows.append([size, L, k, round(dp, 3), int(nodes), "OOM", "", ""])
                    print(f"{size:>7} {L:>4} {k:>2} | {dp:>8.2f} {nodes:>8.0f} | "
                          f"{'OOM':>9} {'-':>9} | {'-':>6}", flush=True)
        del index
        gc.collect()
    if csv_path:
        write_csv(csv_path, ["dict_size", "prefix_len", "k", "dp_ms", "dp_nodes",
                             "naive_ms", "naive_generated", "speedup"], rows)


# ------------------------------------------------------------- 4. symspell --

def benchmark_symspell(sizes, n_queries, repeats, max_depth, csv_path=None):
    """get_noise contre l'index de suppressions, le concurrent serieux.

    On mesure aussi ce que SymSpell coute AVANT la premiere requete : temps de
    construction et nombre d'entrees indexees. C'est la vraie difference de
    nature -- le trie garde les prefixes factorises, SymSpell les materialise a
    plat avec toutes leurs suppressions.
    """
    print("=== 4. SYMSPELL (index de suppressions) ===")
    hdr = (f"{'dico':>7} {'k':>2} | {'index s':>8} {'entrees':>10} | {'|q|':>4} | "
           f"{'DP ms':>8} | {'symspell ms':>11} {'prefixes':>9} | {'gain':>6}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for size in sizes:
        trie, words = load(size)
        for k in RADII:
            t0 = time.perf_counter()
            delete_index, prefix_index, entries = build_delete_index(words, k, max_depth)
            build_s = time.perf_counter() - t0
            for L in PREFIX_LENGTHS:
                if k >= L:
                    continue
                queries = make_queries(words, L, n_queries)
                dp_ms, ss_ms, ss_checked = [], [], []
                for q in queries:
                    dp_ms.append(timeit(lambda: trie.get_noise(q, k, max_depth), repeats))
                    ss_ms.append(timeit(
                        lambda: symspell_candidates(q, delete_index, prefix_index, k, max_depth),
                        repeats))
                    ss_checked.append(
                        symspell_candidates(q, delete_index, prefix_index, k, max_depth)[1])
                dp = statistics.median(dp_ms)
                ss = statistics.median(ss_ms)
                chk = statistics.median(ss_checked)
                rows.append([size, k, round(build_s, 2), entries, L,
                             round(dp, 3), round(ss, 3), int(chk), round(ss / dp, 2)])
                print(f"{size:>7} {k:>2} | {build_s:>8.2f} {entries:>10,} | {L:>4} | "
                      f"{dp:>8.2f} | {ss:>11.2f} {chk:>9.0f} | {ss / dp:>5.1f}x",
                      flush=True)
            del delete_index, prefix_index
            gc.collect()
    if csv_path:
        write_csv(csv_path, ["dict_size", "k", "index_build_s", "index_entries",
                             "prefix_len", "dp_ms", "symspell_ms",
                             "symspell_prefixes_checked", "symspell_over_dp"], rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=SIZES)
    ap.add_argument("--queries", type=int, default=10, help="requetes par cellule (section 3)")
    ap.add_argument("--repeats", type=int, default=5, help="mesures par requete (section 3)")
    ap.add_argument("--pairs", type=int, default=60, help="paires du testset (section 2)")
    ap.add_argument("--quality-size", type=int, default=50_000, help="dico de la section 2")
    ap.add_argument("--testset", default="testset1", choices=sorted(TESTSETS),
                    help="jeu d'evaluation de la section 2")
    ap.add_argument("--max-depth", type=int, default=3,
                    help="caracteres autorises au-dela de la requete (-1 = sans limite)")
    ap.add_argument("--skip", nargs="*", default=[],
                    choices=["test", "quality", "bench", "symspell"])
    ap.add_argument("--no-csv", action="store_true", help="ne pas ecrire results/*.csv")
    ap.add_argument("--scale-check", action="store_true",
                    help="verifie aussi la correction a 100k et 333k (lent : force brute)")
    args = ap.parse_args()
    max_depth = None if args.max_depth < 0 else args.max_depth

    if "test" not in args.skip:
        test_correctness(max_depth)
        if args.scale_check:
            test_scale(max_depth)
    if "quality" not in args.skip:
        quality(args.quality_size, args.pairs, max_depth,
                None if args.no_csv else RESULTS / f"quality_{args.testset}.csv",
                testset=args.testset)
    if "bench" not in args.skip:
        benchmark(args.sizes, args.queries, args.repeats, max_depth,
                  None if args.no_csv else RESULTS / "benchmark.csv")
    if "symspell" not in args.skip:
        benchmark_symspell(args.sizes, args.queries, args.repeats, max_depth,
                           None if args.no_csv else RESULTS / "symspell.csv")


if __name__ == "__main__":
    main()
