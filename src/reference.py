"""Brute-force ground truth for error-tolerant prefix search.

Two implementations on purpose:

  reference_search        uses osa_row(), the same "last row = distances to all
                          prefixes" property search_dp relies on.
  reference_search_naive  shares nothing: it slices each prefix and calls osa()
                          on it.

search_dp is checked against the first, and the first against the second. Skip
that second step and the gate is circular -- a wrong property would make both
the reference and search_dp wrong identically, and every test would pass.
"""
from utils import osa, osa_row


def reference_search(query, words, max_dist, max_completion=None):
    """{ w : some prefix p of w has osa(query, p) <= max_dist }."""
    out = set()
    for w in words:
        row = osa_row(query, w)
        for j, d in enumerate(row):
            if d <= max_dist and (max_completion is None or len(w) - j <= max_completion):
                out.add(w)
                break
    return out


def reference_search_naive(query, words, max_dist, max_completion=None):
    """Same set, by explicit prefix slicing. Deliberately slow -- small dicts only."""
    out = set()
    for w in words:
        for j in range(len(w) + 1):
            if max_completion is not None and len(w) - j > max_completion:
                continue
            if osa(query, w[:j]) <= max_dist:
                out.add(w)
                break
    return out


def min_prefix_distance_naive(query, word):
    """min over prefixes, by explicit slicing."""
    return min(osa(query, word[:j]) for j in range(len(word) + 1))
