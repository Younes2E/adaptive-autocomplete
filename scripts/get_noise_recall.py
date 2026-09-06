"""get_noise is not correctness-equivalent, so it is excluded from the gate.
Its honest characterisation is recall against the reference set: what fraction
of the true answers does the hand-rolled recursion actually find, and how many
out-of-radius extras does it return?
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd                              # noqa: E402
from dataset import load_trie, load_vocab        # noqa: E402
from queries import cells, make_queries          # noqa: E402
from reference import reference_search           # noqa: E402

SIZE = 20_000

def main():
    trie, vocab = load_trie(SIZE), load_vocab(SIZE)
    rows = []
    for L, k in cells():
        for q in make_queries(vocab, L, 4):
            ref = reference_search(q, vocab, k)
            gn = {r[0] for r in trie.get_noise(q, distance=k)}
            dp = {r[0] for r in trie.search_dp(q, max_dist=k)}
            if not ref:
                continue
            rows.append({
                "prefix_len": L, "k": k,
                "gn_recall": len(gn & ref) / len(ref),
                "gn_precision": len(gn & ref) / len(gn) if gn else 0.0,
                "dp_recall": len(dp & ref) / len(ref),
                "gn_extra": len(gn - ref), "ref_size": len(ref),
            })
    df = pd.DataFrame(rows)
    out = (df.groupby(["k", "prefix_len"])
             .agg(n=("gn_recall", "size"), ref=("ref_size", "median"),
                  gn_recall=("gn_recall", "mean"), gn_prec=("gn_precision", "mean"),
                  gn_extra=("gn_extra", "median"), dp_recall=("dp_recall", "mean"))
             .reset_index())
    print(f"get_noise vs reference set (dict={SIZE})\n")
    print(f"{'k':>2} {'|q|':>4} {'ref':>7} {'gn recall':>10} {'gn prec':>9} "
          f"{'gn extra':>9} {'dp recall':>10}")
    print("-" * 56)
    for _, r in out.iterrows():
        print(f"{int(r.k):>2} {int(r.prefix_len):>4} {r.ref:>7.0f} {r.gn_recall:>9.1%} "
              f"{r.gn_prec:>8.1%} {r.gn_extra:>9.0f} {r.dp_recall:>9.1%}")
    df.to_csv(ROOT / "results" / "get_noise_recall.csv", index=False)
    print(f"\nwrote results/get_noise_recall.csv")

if __name__ == "__main__":
    main()
