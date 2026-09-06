"""T3 -- scaling benchmark: search_dp vs generate-and-lookup vs get_noise.

Axes: dictionary size x edit radius k x query prefix length, restricted to
non-degenerate cells (k < |q|).

Metrics, in order of trustworthiness:
  visited_nodes / dp_cells    hardware- and language-independent (primary)
  pruned_subtrees, emitted_subtrees   where the gain comes from
  candidates_generated        the baseline's explosion
  latency median + p95 (ms)   wall-clock CPU cost, for comparison with other
                              systems later; machine specs go in the manifest.
                              search_dp runs with_ops=False: retrieval only,
                              like the baseline, which yields no channel labels
  throughput (queries/s)
  n_results                   without it, latencies are not comparable
"""
import argparse
import gc
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd                                   # noqa: E402

from baseline import build_prefix_index, baseline_search   # noqa: E402
from dataset import load_trie, load_vocab, DICT_SIZES      # noqa: E402
from queries import cells, make_queries                    # noqa: E402

# The prefix index materialises every (prefix, word) pair; beyond this size it
# exhausts memory. Reported as a finding, not hidden.
BASELINE_MAX_SIZE = 100_000


def time_call(fn, repeats, warmup=1):
    """Median and p95 seconds per call. Warmup runs are discarded and the GC is
    disabled during timing so a collection cannot land inside one sample."""
    for _ in range(warmup):
        fn()
    samples = []
    gc.collect()
    gc_was_on = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repeats):
            t0 = time.perf_counter()
            fn()
            samples.append(time.perf_counter() - t0)
    finally:
        if gc_was_on:
            gc.enable()
    samples.sort()
    p95 = samples[min(len(samples) - 1, int(0.95 * (len(samples) - 1)))]
    return statistics.median(samples), p95


def bench_cell(method, trie, index, queries, k, repeats):
    rows = []
    for q in queries:
        rec = {"query": q, "prefix_len": len(q), "k": k, "method": method,
               "status": "ok"}
        try:
            if method == "search_dp":
                res = trie.search_dp(q, max_dist=k, with_ops=False)
                st = dict(trie.stats)
                rec.update(st)
                rec["n_results"] = len({r[0] for r in res})
                med, p95 = time_call(lambda: trie.search_dp(q, max_dist=k, with_ops=False), repeats)
            elif method == "baseline":
                if index is None:
                    rec["status"] = "oom"
                    rows.append(rec)
                    continue
                gen, uniq = baseline_search(q, index, max_dist=k, count_only=True)
                rec["candidates_generated"] = gen
                rec["n_results"] = uniq
                med, p95 = time_call(lambda: baseline_search(q, index, max_dist=k), repeats)
            else:  # get_noise -- not correctness-equivalent, kept as a third point
                res = trie.get_noise(q, distance=k)
                rec["n_results"] = len({r[0] for r in res})
                med, p95 = time_call(lambda: trie.get_noise(q, distance=k), repeats)
            rec["latency_ms"] = med * 1e3
            rec["latency_p95_ms"] = p95 * 1e3
            rec["throughput_qps"] = 1.0 / med if med else float("nan")
        except MemoryError:
            rec["status"] = "oom"
        except Exception as exc:                       # keep the sweep alive
            rec["status"] = f"error: {type(exc).__name__}"
        rows.append(rec)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=DICT_SIZES)
    ap.add_argument("--queries", type=int, default=10)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--methods", nargs="+",
                    default=["search_dp", "baseline", "get_noise"])
    ap.add_argument("--out", default=str(ROOT / "results"))
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_rows, index_rows = [], []

    for size in args.sizes:
        print(f"\n=== dictionary {size} ===", flush=True)
        trie = load_trie(size)
        vocab = load_vocab(size)

        index = None
        if "baseline" in args.methods:
            if size <= BASELINE_MAX_SIZE:
                tracemalloc.start()
                t0 = time.perf_counter()
                index = build_prefix_index(vocab)
                build_s = time.perf_counter() - t0
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                index_rows.append({"dict_size": size, "index_build_s": build_s,
                                   "index_peak_mb": peak / 1e6, "status": "ok"})
                print(f"  prefix index: {build_s:.1f}s, peak {peak/1e6:.0f} MB", flush=True)
            else:
                index_rows.append({"dict_size": size, "index_build_s": float("nan"),
                                   "index_peak_mb": float("nan"), "status": "skipped_oom"})
                print(f"  prefix index: SKIPPED (> {BASELINE_MAX_SIZE} words)", flush=True)

        for L, k in cells():
            queries = make_queries(vocab, L, args.queries)
            if not queries:
                continue
            for method in args.methods:
                rows = bench_cell(method, trie, index, queries, k, args.repeats)
                for r in rows:
                    r["dict_size"] = size
                all_rows.extend(rows)
            done = [r for r in all_rows if r["dict_size"] == size
                    and r["prefix_len"] == L and r["k"] == k and r["status"] == "ok"]
            if done:
                summary = {m: statistics.median(
                    [r["latency_ms"] for r in done if r["method"] == m] or [float("nan")])
                    for m in args.methods}
                print(f"  |q|={L} k={k}  " + "  ".join(
                    f"{m}={summary[m]:.2f}ms" for m in args.methods), flush=True)

        del index
        gc.collect()

    raw = pd.DataFrame(all_rows)
    raw.to_csv(out_dir / "benchmark_raw.csv", index=False)

    ok = raw[raw["status"] == "ok"]
    agg = (ok.groupby(["dict_size", "prefix_len", "k", "method"])
             .agg(latency_ms=("latency_ms", "median"),
                  latency_p95_ms=("latency_p95_ms", "median"),
                  throughput_qps=("throughput_qps", "median"),
                  n_results=("n_results", "median"),
                  visited_nodes=("visited_nodes", "median"),
                  dp_cells=("dp_cells", "median"),
                  pruned_subtrees=("pruned_subtrees", "median"),
                  emitted_subtrees=("emitted_subtrees", "median"),
                  candidates_generated=("candidates_generated", "median"))
             .reset_index())
    agg.to_csv(out_dir / "benchmark_agg.csv", index=False)
    pd.DataFrame(index_rows).to_csv(out_dir / "baseline_index_cost.csv", index=False)

    print(f"\nwrote {out_dir/'benchmark_raw.csv'} ({len(raw)} rows)")
    print(f"wrote {out_dir/'benchmark_agg.csv'} ({len(agg)} rows)")
    print(f"machine: {platform.platform()} / {platform.processor() or platform.machine()}")


if __name__ == "__main__":
    main()
