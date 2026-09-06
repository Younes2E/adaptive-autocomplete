"""T5 -- quality evaluation for error-tolerant autocompletion.

Metrics (state-of-the-art set, comparable to Kernighan et al. 1990 and
Brill & Moore 2000):
  recall        is the intended correction in the candidate set at all? This
                bounds everything else and is the retrieval-side number.
  top-1/2/3     accuracy after noisy-channel ranking
  MRR           mean reciprocal rank -- degrades gracefully where top-1 is
                degenerate, which it is for short prefixes
  precision@k   |relevant in top k| / k, here 1/k when the answer is found

Results are broken down BY PREFIX LENGTH. Aggregating hides the fact that top-1
at |q|=2 is near-zero by nature: thousands of words share a 2-letter prefix, so
no ranker can do better. That is a property of the task, not of the system.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np                                  # noqa: E402
import pandas as pd                                 # noqa: E402

from confusion import Confusion                     # noqa: E402
from dataset import load_trie, load_vocab           # noqa: E402
from noisy_channel import prior, editprob           # noqa: E402
from utils import softmax                           # noqa: E402

TESTSETS = {
    "spell-errors": ("data/test/spell-errors.txt", ","),
    "testset1": ("data/test/spell-testset1.txt", " "),
    "testset2": ("data/test/spell-testset2.txt", " "),
}


def load_pairs(path, sep):
    """'correct: wrong1, wrong2' or 'correct: wrong1 wrong2' -> [(wrong, right)].

    spell-errors.txt separates variants with commas and may append '*N'
    occurrence counts; the testsets use spaces. Both are handled.
    """
    pairs = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            right, wrongs = line.split(":", 1)
            right = right.strip().lower()
            for tok in wrongs.replace(",", " ").split():
                tok = tok.split("*")[0].strip().lower()
                if tok and tok.isalpha() and right.isalpha():
                    pairs.append((tok, right))
    return pairs


def rank(candidates, trie, confusion, n=3):
    """Noisy-channel ranking: log prior + log channel, then softmax."""
    if not candidates:
        return []
    scores = np.empty(len(candidates))
    for i, c in enumerate(candidates):
        try:
            p = float(editprob(c, confusion))
        except Exception:
            p = 1e-12
        p = max(p, 1e-12)
        scores[i] = np.log(prior(trie, c)) + np.log(p)
    order = np.argsort(softmax(scores))[::-1]
    out, seen = [], set()
    for i in order:
        w = candidates[i][0]
        if w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= n:
            break
    return out


def evaluate(trie, confusion, pairs, k, max_prefix=7, topn=3, limit=None):
    rows = []
    for wrong, right in (pairs[:limit] if limit else pairs):
        for L in range(2, min(len(wrong), max_prefix) + 1):
            if k >= L:                     # degenerate cell, see queries.py
                continue
            q = wrong[:L]
            cands = trie.search_dp(q, max_dist=k)
            names = [c[0] for c in cands]
            found = right in set(names)
            best = rank(cands, trie, confusion, n=topn) if found or names else []
            rr = 0.0
            if right in best:
                rr = 1.0 / (best.index(right) + 1)
            rows.append({
                "prefix_len": L, "k": k, "wrong": wrong, "right": right,
                "n_candidates": len(set(names)),
                "recall": int(found),
                "top1": int(len(best) > 0 and best[0] == right),
                "top2": int(right in best[:2]),
                "top3": int(right in best[:3]),
                "rr": rr,
            })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default="testset1", choices=list(TESTSETS))
    ap.add_argument("--dict-size", type=int, default=50_000)
    ap.add_argument("--k", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--limit", type=int, default=150)
    ap.add_argument("--out", default=str(ROOT / "results" / "accuracy.csv"))
    args = ap.parse_args()

    path, sep = TESTSETS[args.testset]
    pairs = load_pairs(ROOT / path, sep)
    trie = load_trie(args.dict_size)
    vocab = set(load_vocab(args.dict_size))
    confusion = Confusion()

    # A correction absent from the dictionary is unreachable; excluding it keeps
    # the numbers about the ranker rather than about dictionary coverage.
    kept = [(w, r) for w, r in pairs if r in vocab]
    print(f"{args.testset}: {len(pairs)} pairs, {len(kept)} kept "
          f"({len(pairs)-len(kept)} dropped: correction not in {args.dict_size}-word dict)")

    frames = []
    for k in args.k:
        df = evaluate(trie, confusion, kept, k, limit=args.limit)
        df["testset"] = args.testset
        df["dict_size"] = args.dict_size
        frames.append(df)

    full = pd.concat(frames, ignore_index=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(args.out, index=False)

    summary = (full.groupby(["k", "prefix_len"])
                   .agg(n=("recall", "size"), cands=("n_candidates", "median"),
                        recall=("recall", "mean"), top1=("top1", "mean"),
                        top2=("top2", "mean"), top3=("top3", "mean"),
                        mrr=("rr", "mean"))
                   .reset_index())
    print(f"\n{'k':>2} {'|q|':>4} {'n':>5} {'cands':>7} {'recall':>7} "
          f"{'top-1':>7} {'top-2':>7} {'top-3':>7} {'MRR':>7}")
    print("-" * 62)
    for _, r in summary.iterrows():
        print(f"{int(r.k):>2} {int(r.prefix_len):>4} {int(r.n):>5} {r.cands:>7.0f} "
              f"{r.recall:>6.1%} {r.top1:>6.1%} {r.top2:>6.1%} {r.top3:>6.1%} {r.mrr:>7.3f}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
