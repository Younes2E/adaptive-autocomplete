"""Figures for the paper, from results/benchmark_agg.csv."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt      # noqa: E402
import pandas as pd                  # noqa: E402

FIG = ROOT / "figures"
STYLE = {"search_dp": ("o-", "#1f77b4"), "baseline": ("s--", "#d62728"),
         "get_noise": ("^:", "#7f7f7f")}


def fig_latency_vs_dictsize(agg):
    """Main figure: latency vs dictionary size, log scale, one curve per method."""
    for k in sorted(agg.k.unique()):
        sub = agg[(agg.k == k) & (agg.prefix_len == 5)]
        if sub.empty:
            continue
        fig, ax = plt.subplots(figsize=(5, 3.4))
        for m, (mk, col) in STYLE.items():
            d = sub[sub.method == m].sort_values("dict_size")
            if d.empty:
                continue
            ax.plot(d.dict_size, d.latency_ms, mk, color=col, label=m, ms=5)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("dictionary size (words)"); ax.set_ylabel("latency (ms)")
        ax.set_title(f"Query latency vs dictionary size (k={k}, |q|=5)")
        ax.grid(alpha=.3, which="both"); ax.legend()
        fig.tight_layout(); fig.savefig(FIG / f"fig_latency_vs_dictsize_k{k}.png", dpi=150)
        plt.close(fig)


def fig_prefix_length(agg):
    """The money figure: the baseline collapses as the prefix lengthens."""
    sub = agg[(agg.dict_size == agg.dict_size.max()) & (agg.k == 2)]
    if sub.empty:
        sub = agg[agg.k == 2]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    for m, (mk, col) in STYLE.items():
        d = sub[sub.method == m].sort_values("prefix_len")
        if d.empty:
            continue
        axes[0].plot(d.prefix_len, d.latency_ms, mk, color=col, label=m, ms=5)
    axes[0].set_yscale("log"); axes[0].set_xlabel("query prefix length")
    axes[0].set_ylabel("latency (ms)"); axes[0].set_title("Latency (k=2)")
    axes[0].grid(alpha=.3, which="both"); axes[0].legend()

    d = sub[sub.method == "search_dp"].sort_values("prefix_len")
    b = sub[sub.method == "baseline"].sort_values("prefix_len")
    if not d.empty:
        axes[1].plot(d.prefix_len, d.visited_nodes, "o-", color="#1f77b4",
                     label="search_dp: nodes visited", ms=5)
    if not b.empty and b.candidates_generated.notna().any():
        axes[1].plot(b.prefix_len, b.candidates_generated, "s--", color="#d62728",
                     label="baseline: candidates generated", ms=5)
    axes[1].set_yscale("log"); axes[1].set_xlabel("query prefix length")
    axes[1].set_ylabel("work units"); axes[1].set_title("Work performed (k=2)")
    axes[1].grid(alpha=.3, which="both"); axes[1].legend()
    fig.tight_layout(); fig.savefig(FIG / "fig_prefix_length.png", dpi=150)
    plt.close(fig)


def fig_pruning(agg):
    sub = agg[(agg.method == "search_dp") & (agg.k == 2)]
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(5, 3.4))
    for size in sorted(sub.dict_size.unique()):
        d = sub[sub.dict_size == size].sort_values("prefix_len")
        ax.plot(d.prefix_len, d.pruned_subtrees, "o-", ms=4, label=f"{size//1000}k")
    ax.set_xlabel("query prefix length"); ax.set_ylabel("pruned subtrees")
    ax.set_title("Where the gain comes from (k=2)")
    ax.grid(alpha=.3); ax.legend(title="dictionary")
    fig.tight_layout(); fig.savefig(FIG / "fig_pruning.png", dpi=150)
    plt.close(fig)


def main():
    FIG.mkdir(exist_ok=True)
    path = ROOT / "results" / "benchmark_agg.csv"
    if not path.exists():
        print("no benchmark_agg.csv; run scripts/benchmark.py first")
        return 1
    agg = pd.read_csv(path)
    fig_latency_vs_dictsize(agg)
    fig_prefix_length(agg)
    fig_pruning(agg)
    print("figures written to", FIG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
