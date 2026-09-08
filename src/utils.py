import numpy as np


def softmax(x):
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
    n, m = len(a), len(b)
    prev2 = None
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev


def osa(a, b):
    """Distance d'edition OSA entre deux chaines."""
    return osa_row(a, b)[-1]
