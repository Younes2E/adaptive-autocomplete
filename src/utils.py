import numpy as np

def softmax(x):
    # Subtract the max before exponentiating: with thousands of candidates the
    # log-scores are very negative and the raw sum underflows to 0, giving nan.
    # Shifting by the max is mathematically a no-op for softmax.
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    shifted = np.exp(x - np.max(x))
    return shifted / shifted.sum()

def truncate_proba(p, decimals=2):
    n_zeros = max(0, int(-np.floor(np.log10(p))-1))
    n_decimals = max(decimals, n_zeros+2)
    factor = 10 ** n_decimals
    return np.floor(p * factor)/factor


def osa_row(a, b):
    """Last row of the OSA matrix: [osa(a, b[:j]) for j in 0..len(b)].

    Optimal String Alignment is Damerau-Levenshtein restricted so that no
    substring is edited twice; that restriction is what lets a single row be
    carried down a trie branch, and it is why osa("rf", "for") == 3 while
    unrestricted Damerau gives 2.
    """
    n, m = len(a), len(b)
    prev2 = None
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1,         # deletion
                         cur[j - 1] + 1,      # insertion
                         prev[j - 1] + cost)  # match / substitution
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)   # transposition
        prev2, prev = prev, cur
    return prev


def osa(a, b):
    """OSA edit distance between two full strings."""
    return osa_row(a, b)[-1]


def min_prefix_distance(query, word):
    """min over every prefix p of `word` of osa(query, p).

    The last matrix row read across j already holds osa(query, word[:j]) for
    every j, so one pass answers the whole existential.
    """
    return min(osa_row(query, word))
