"""Figures du papier, regenerees depuis results/benchmark.csv.

    python make_figures.py            # apres un run complet de bench.py

Produit dans figures/ :
  fig_prefix_length.png        figure principale : latence + travail vs |q| (k=2)
  fig_pruning.png              noeuds visites vs |q|, l'elagage vu de pres
  fig_latency_vs_dictsize_k2.png   latence vs taille de dico a k=2
  fig_latency_vs_dictsize_k1.png   idem a k=1, ou la baseline gagne
  fig_tradeoff.png             memoire vs latence face a SymSpell

Conventions de couleur : `get_noise` est une rampe bleue ordonnee par taille de
dictionnaire (grandeur ordonnee), la baseline est orange (autre entite). Jamais
deux echelles y sur un meme axe : chaque mesure a son panneau.
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "results" / "benchmark.csv"
CSV_SYMSPELL = ROOT / "results" / "symspell.csv"
CSV_MEMORY = ROOT / "results" / "memory.csv"
FIGURES = ROOT / "figures"

# Palette validee (validate_palette.js, mode light) : rampe bleue ordinale pour
# les tailles de dictionnaire, orange categoriel pour la baseline.
DICT_COLORS = {10000: "#86b6ef", 50000: "#5598e7", 100000: "#2a78d6", 333333: "#184f95"}
NAIVE = "#eb6834"
SYMSPELL = "#1baf7a"      # slot 3 categoriel : distinct de bleu et orange
INK = "#0b0b0b"
INK_SOFT = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

LABEL = {10000: "10k", 50000: "50k", 100000: "100k", 333333: "333k"}


def load():
    with open(CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["dict_size"] = int(r["dict_size"])
        r["prefix_len"] = int(r["prefix_len"])
        r["k"] = int(r["k"])
        r["dp_ms"] = float(r["dp_ms"])
        r["dp_nodes"] = int(r["dp_nodes"])
        r["oom"] = r["naive_ms"] == "OOM"
        r["naive_ms"] = None if r["oom"] else float(r["naive_ms"])
        r["naive_generated"] = None if r["oom"] else int(r["naive_generated"])
    return rows


def style(ax, xlabel, ylabel, title=None, int_x=False):
    """Grille et axes recessifs : les marques portent l'information, pas le cadre."""
    ax.set_facecolor(SURFACE)
    if int_x:
        ax.set_xticks([3, 4, 5, 6, 7])
    ax.grid(True, axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=9, length=0)
    ax.set_xlabel(xlabel, color=INK_SOFT, fontsize=9.5)
    ax.set_ylabel(ylabel, color=INK_SOFT, fontsize=9.5)
    if title:
        ax.set_title(title, color=INK, fontsize=11, loc="left", pad=10)


def sizes_of(rows):
    return sorted({r["dict_size"] for r in rows})


def series(rows, size, k, field):
    sel = sorted((r for r in rows if r["dict_size"] == size and r["k"] == k),
                 key=lambda r: r["prefix_len"])
    xs = [r["prefix_len"] for r in sel if r[field] is not None]
    ys = [r[field] for r in sel if r[field] is not None]
    return xs, ys


def fig_prefix_length(rows):
    """Figure principale : les deux couts vont dans des directions opposees.

    Meme code couleur dans les deux panneaux (rampe bleue = get_noise par taille
    de dico, orange = baseline), donc une seule legende partagee en bas.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.4), facecolor=SURFACE)

    for size in sizes_of(rows):
        xs, ys = series(rows, size, 2, "dp_ms")
        ax1.plot(xs, ys, color=DICT_COLORS[size], linewidth=2, marker="o",
                 markersize=5, label=f"get_noise, dico {LABEL[size]}", zorder=3)
    # La baseline ne depend pas de la taille du dico (ecart < 3 % entre 10k et
    # 100k) : une seule courbe, prise a 100k.
    xs, ys = series(rows, 100000, 2, "naive_ms")
    ax1.plot(xs, ys, color=NAIVE, linewidth=2, marker="s", markersize=5,
             label="baseline naive", zorder=3)
    ax1.set_yscale("log")
    ax1.set_xlim(2.75, 7.95)
    style(ax1, "longueur du prefixe |q|", "latence (ms, echelle log)",
          "a. Latence a k=2", int_x=True)
    # Ecart direct entre les deux extremes a |q|=7, la ou l'argument est le plus net.
    ax1.annotate("", xy=(7.35, 451.28), xytext=(7.35, 3.25),
                 arrowprops=dict(arrowstyle="<->", color=INK_SOFT, lw=1.1))
    ax1.text(7.5, 38, "139x", color=INK, fontsize=10, fontweight="bold",
             va="center")

    for size in sizes_of(rows):
        xs, ys = series(rows, size, 2, "dp_nodes")
        ax2.plot(xs, ys, color=DICT_COLORS[size], linewidth=2, marker="o",
                 markersize=5, zorder=3)
    xs, ys = series(rows, 100000, 2, "naive_generated")
    ax2.plot(xs, ys, color=NAIVE, linewidth=2, marker="s", markersize=5, zorder=3)
    ax2.set_yscale("log")
    ax2.set_xlim(2.75, 7.95)
    style(ax2, "longueur du prefixe |q|",
          "travail effectue (echelle log)",
          "b. Travail : noeuds visites vs chaines generees", int_x=True)
    ax2.text(7.0, 78000, "generees", color=NAIVE, fontsize=9,
             ha="right", va="bottom")
    ax2.text(7.0, 30000, "noeuds", color=DICT_COLORS[333333], fontsize=9,
             ha="right", va="top")

    handles = [plt.Line2D([], [], color=DICT_COLORS[s_], linewidth=2, marker="o",
                          markersize=5, label=f"get_noise, dico {LABEL[s_]}")
               for s_ in sizes_of(rows)]
    handles.append(plt.Line2D([], [], color=NAIVE, linewidth=2, marker="s",
                              markersize=5, label="baseline naive"))
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False,
               fontsize=9, labelcolor=INK_SOFT, bbox_to_anchor=(0.5, -0.01))

    fig.suptitle("Le cout de la baseline croit avec |q|, le notre decroit",
                 color=INK, fontsize=12.5, x=0.008, ha="left", y=0.995)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    save(fig, "fig_prefix_length.png")


def fig_pruning(rows):
    """Noeuds visites : plus la requete est longue, plus l'elagage mord tot."""
    fig, ax = plt.subplots(figsize=(7, 4.1), facecolor=SURFACE)
    lengths = sorted({r["prefix_len"] for r in rows})
    all_sizes = sizes_of(rows)
    width = 0.8 / len(all_sizes)
    for i, size in enumerate(all_sizes):
        xs, ys = series(rows, size, 2, "dp_nodes")
        offset = (i - (len(all_sizes) - 1) / 2) * width
        ax.bar([x + offset for x in xs], ys, width=width * 0.92,
               color=DICT_COLORS[size], label=f"dico {LABEL[size]}", zorder=3)
    ax.set_xticks(lengths)
    style(ax, "longueur du prefixe |q|", "noeuds du trie examines",
          "L'elagage : le travail decroit quand la requete s'allonge (k=2)")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT, ncol=2)
    drop = 1 - 37799 / 102420
    ax.annotate(f"-{drop:.0%} de |q|=3 a |q|=7 (dico 333k)", xy=(3.55, 70000),
                color=INK_SOFT, fontsize=9.5)
    fig.tight_layout()
    save(fig, "fig_pruning.png")


def fig_latency_vs_dictsize(rows, k):
    """Latence vs taille de dictionnaire, a |q|=5 : deux moteurs de cout."""
    fig, ax = plt.subplots(figsize=(7, 4.1), facecolor=SURFACE)
    sel = sorted((r for r in rows if r["k"] == k and r["prefix_len"] == 5),
                 key=lambda r: r["dict_size"])
    xs = [r["dict_size"] for r in sel]
    ax.plot(xs, [r["dp_ms"] for r in sel], color="#2a78d6", linewidth=2,
            marker="o", markersize=6, label="get_noise (DP sur trie)", zorder=3)
    nx = [r["dict_size"] for r in sel if not r["oom"]]
    ax.plot(nx, [r["naive_ms"] for r in sel if not r["oom"]], color=NAIVE,
            linewidth=2, marker="s", markersize=6, label="baseline naive", zorder=3)

    oom = [r for r in sel if r["oom"]]
    if oom and nx:
        last = [r["naive_ms"] for r in sel if not r["oom"]][-1]
        ax.plot([nx[-1], oom[0]["dict_size"]], [last, last], color=NAIVE,
                linewidth=1.6, linestyle=":", zorder=2)
        ax.plot([oom[0]["dict_size"]], [last], color=NAIVE, marker="x",
                markersize=10, markeredgewidth=2.5, zorder=4)
        ax.annotate("OOM : l'index prefixe\nne tient plus en memoire",
                    xy=(oom[0]["dict_size"], last), xytext=(-14, -26),
                    textcoords="offset points", ha="right", va="top",
                    color=NAIVE, fontsize=9)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels([LABEL[x] for x in xs])
    verdict = ("la baseline reste devant" if k == 1 else "l'ecart se resserre mais tient")
    style(ax, "taille du dictionnaire (mots)", "latence (ms, echelle log)",
          f"Passage a l'echelle a k={k}, |q|=5 : {verdict}")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT)
    fig.tight_layout()
    save(fig, f"fig_latency_vs_dictsize_k{k}.png")


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fig_tradeoff():
    """La figure du nouveau positionnement : SymSpell est rapide, mais gros.

    Deux panneaux sur le meme axe x. A gauche ce que la structure coute en
    memoire, a droite ce qu'elle rend en latence. L'argument du papier est le
    couple, pas l'une des deux moities.
    """
    if not (CSV_SYMSPELL.exists() and CSV_MEMORY.exists()):
        print("  (fig_tradeoff : results/symspell.csv ou memory.csv absent, ignoree)")
        return
    mem = read_csv(CSV_MEMORY)
    ss = read_csv(CSV_SYMSPELL)
    dp = read_csv(CSV)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.4), facecolor=SURFACE)

    def mem_series(structure, k=""):
        pts = sorted((int(r["dict_size"]), float(r["index_gb"])) for r in mem
                     if r["structure"] == structure and r["k"] == str(k))
        return [p[0] for p in pts], [p[1] for p in pts]

    xs, ys = mem_series("trie")
    ax1.plot(xs, ys, color="#2a78d6", linewidth=2, marker="o", markersize=6,
             label="trie", zorder=3)
    for k, style_ in ((1, "--"), (2, "-")):
        xs, ys = mem_series("symspell", k)
        if xs:
            ax1.plot(xs, ys, color=SYMSPELL, linewidth=2, marker="^", markersize=6,
                     linestyle=style_, label=f"SymSpell k={k}", zorder=3)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xticks([10000, 50000, 100000, 333333])
    ax1.set_xticklabels(["10k", "50k", "100k", "333k"])
    style(ax1, "taille du dictionnaire (mots)", "memoire de la structure (Go)",
          "a. Ce que la structure coute")
    ax1.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT)

    def lat(rows, field, source):
        pts = sorted((int(r["dict_size"]), float(r[field])) for r in rows
                     if r["prefix_len"] == "5" and r["k"] == "2"
                     and r[field] not in ("", "OOM"))
        return [p[0] for p in pts], [p[1] for p in pts]

    xs, ys = lat(dp, "dp_ms", None)
    ax2.plot(xs, ys, color="#2a78d6", linewidth=2, marker="o", markersize=6,
             label="get_noise (trie)", zorder=3)
    xs, ys = lat(ss, "symspell_ms", None)
    ax2.plot(xs, ys, color=SYMSPELL, linewidth=2, marker="^", markersize=6,
             label="SymSpell", zorder=3)
    xs, ys = lat(dp, "naive_ms", None)
    ax2.plot(xs, ys, color=NAIVE, linewidth=2, marker="s", markersize=6,
             label="baseline naive", zorder=3)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xticks([10000, 50000, 100000, 333333])
    ax2.set_xticklabels(["10k", "50k", "100k", "333k"])
    style(ax2, "taille du dictionnaire (mots)", "latence (ms, echelle log)",
          "b. Ce qu'elle rend (|q|=5, k=2)")
    ax2.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT)

    fig.suptitle("SymSpell est plus rapide a la requete, pour 20x la memoire",
                 color=INK, fontsize=12.5, x=0.008, ha="left", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "fig_tradeoff.png")


def save(fig, name):
    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {path.relative_to(ROOT)}")


def main():
    if not CSV.exists():
        raise SystemExit(f"{CSV} absent : lancer d'abord `python bench.py`")
    rows = load()
    print(f"=== FIGURES (depuis {CSV.relative_to(ROOT)}) ===")
    fig_prefix_length(rows)
    fig_pruning(rows)
    for k in (2, 1):
        fig_latency_vs_dictsize(rows, k)
    fig_tradeoff()


if __name__ == "__main__":
    main()
