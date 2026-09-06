"""T2 -- generate-and-lookup baseline (Kernighan, Church & Gale 1990, section 2).

For plain correction this is competitive: enumerate every variant within k edits
and test each against a set. For the autocompletion task it must additionally
expand every variant by all of its dictionary completions, and that product is
what collapses -- the measurement this project is built around.
"""
from collections import defaultdict

from utils import osa

ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def edits1(word):
    """Every string one edit from `word` (delete, transpose, replace, insert)."""
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in ALPHABET]
    inserts = [L + c + R for L, R in splits for c in ALPHABET]
    return set(deletes + transposes + replaces + inserts)


def edits_upto(word, k):
    """Every string within OSA distance k, as the baseline would enumerate it.

    Composing edits1 twice also reaches strings at OSA distance 3 -- "rf" -> "fr"
    -> "for", which OSA scores 3 because it forbids re-editing the transposed
    substring. Without the final filter the baseline returns a strict superset
    of search_dp and the correctness gate fails, correctly.
    """
    out = {word}
    frontier = {word}
    for _ in range(k):
        frontier = {e for v in frontier for e in edits1(v)}
        out |= frontier
    return {v for v in out if osa(word, v) <= k}


def build_prefix_index(words):
    """prefix -> list of word ids. Word ids rather than strings: at 100k words
    the (prefix, word) product is in the millions of entries."""
    index = defaultdict(list)
    for wid, w in enumerate(words):
        for i in range(len(w) + 1):
            index[w[:i]].append(wid)
    return {"index": dict(index), "words": list(words)}


def baseline_search(query, index, max_dist=2, count_only=False):
    """Variants within k edits, each expanded by all its dictionary completions.

    Returns the set of matching words, or (n_generated, n_unique) when
    count_only -- n_generated is the pre-deduplication candidate count, the
    number that carries the paper's argument.
    """
    table, words = index["index"], index["words"]
    variants = edits_upto(query, max_dist)
    generated = 0
    found = set()
    for v in variants:
        ids = table.get(v)
        if not ids:
            continue
        generated += len(ids)
        found.update(ids)
    if count_only:
        return generated, len(found)
    return {words[i] for i in found}


def generated_count(query, index, max_dist=2):
    """Candidates materialised before deduplication -- the explosion metric."""
    return baseline_search(query, index, max_dist, count_only=True)[0]
