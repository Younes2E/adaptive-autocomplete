from collections import defaultdict

from utils import osa

ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in ALPHABET]
    inserts = [L + c + R for L, R in splits for c in ALPHABET]
    return set(deletes + transposes + replaces + inserts)


def variants(word, k):
    out = {word}
    frontier = {word}
    for _ in range(k):
        frontier = {e for v in frontier for e in edits1(v)}
        out |= frontier
    return {v for v in out if osa(word, v) <= k}, len(out)


def build_prefix_index(words):
    index = defaultdict(list)
    for w in words:
        for i in range(len(w) + 1):
            index[w[:i]].append(w)
    return dict(index)


def naive_candidates(word, index, k=1, max_depth=3):
    max_len = None if max_depth is None else len(word) + max_depth
    vs, enumerated = variants(word, k)
    found = set()
    for v in vs:
        for w in index.get(v, ()):
            if max_len is None or len(w) <= max_len:
                found.add(w)
    return found, enumerated
