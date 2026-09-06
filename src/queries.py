"""Deterministic query generation, shared by the gate, benchmark and evaluation.

The gate must certify exactly the queries the benchmark measures, so both call
this module with the same seed.

Degeneracy rule: only cells with k < |q| are evaluated. When k >= |q| the empty
prefix is within distance k of the query, and every word has the empty prefix,
so the answer is the entire dictionary (verified: q="th", k=2 -> 100% of a 50k
dictionary). Such cells measure nothing.
"""
import random

SEED = 42
PREFIX_LENGTHS = [2, 3, 4, 5, 6, 7]
RADII = [1, 2]
ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def valid_cell(prefix_len, k):
    """A (|q|, k) cell is measurable only when k < |q|."""
    return k < prefix_len


def cells(prefix_lengths=None, radii=None):
    """Every non-degenerate (prefix_len, k) pair."""
    for L in (prefix_lengths or PREFIX_LENGTHS):
        for k in (radii or RADII):
            if valid_cell(L, k):
                yield L, k


def make_queries(vocab, prefix_len, n, seed=SEED, corrupt=True):
    """n prefix queries of exactly `prefix_len` characters.

    Half are clean prefixes of real words, half carry a single typo
    (substitution or transposition) so the radius is actually exercised.
    """
    rng = random.Random(seed + prefix_len)
    pool = [w for w in vocab if len(w) >= prefix_len]
    if not pool:
        return []
    picks = rng.sample(pool, min(n, len(pool)))
    out = []
    for idx, w in enumerate(picks):
        p = w[:prefix_len]
        if not corrupt or idx % 2 == 0:
            out.append(p)
        elif idx % 4 == 1 and prefix_len >= 2:
            i = rng.randrange(prefix_len - 1)          # transposition
            out.append(p[:i] + p[i + 1] + p[i] + p[i + 2:])
        else:
            i = rng.randrange(prefix_len)              # substitution
            out.append(p[:i] + rng.choice(ALPHABET) + p[i + 1:])
    return out
