from collections import defaultdict

from utils import osa


def deletes(word, k):
    out = {word}
    frontier = {word}
    for _ in range(k):
        nxt = {w[:i] + w[i + 1:] for w in frontier for i in range(len(w))}
        out |= nxt
        frontier = nxt
    return out


def build_delete_index(words, k, max_depth=3):
    delete_index = defaultdict(set)
    prefix_index = defaultdict(list)
    seen = set()
    for w in words:
        for i in range(len(w) + 1):
            prefix_index[w[:i]].append(w)
        for i in range(1, len(w) + 1):
            p = w[:i]
            if p in seen: 
                continue
            seen.add(p)
            for d in deletes(p, k):
                delete_index[d].add(p)
    entries = sum(len(v) for v in delete_index.values())
    return dict(delete_index), dict(prefix_index), entries


def symspell_candidates(query, delete_index, prefix_index, k=1, max_depth=3):
    max_len = None if max_depth is None else len(query) + max_depth
    candidate_prefixes = set()
    for d in deletes(query, k):
        candidate_prefixes |= delete_index.get(d, frozenset())

    found = set()
    checked = 0
    for p in candidate_prefixes:
        checked += 1
        if osa(query, p) > k:   
            continue
        for w in prefix_index.get(p, ()):
            if max_len is None or len(w) <= max_len:
                found.add(w)
    return found, checked
