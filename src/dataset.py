"""Dictionary loading with caching.

data/dict/en_freq.txt is Norvig's count_1w.txt: 333k words already sorted by
descending Google frequency, so subsampling by frequency rank is just a prefix
of the file.
"""
from functools import lru_cache
from pathlib import Path

from trie import Trie

DICT_PATH = Path(__file__).resolve().parent.parent / "data" / "dict" / "en_freq.txt"
DICT_SIZES = [10_000, 50_000, 100_000, 333_333]


def load_words(limit=None, path=None):
    """[(word, freq)] for the `limit` most frequent alphabetic words."""
    src = Path(path) if path else DICT_PATH
    out = []
    with open(src, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2 and parts[0].isalpha():
                out.append((parts[0].lower(), int(parts[1])))
                if limit is not None and len(out) >= limit:
                    break
    return out


@lru_cache(maxsize=8)
def load_trie(limit=None, path=None):
    """Cached trie. Building 333k words is slow; benchmark cells reuse this."""
    t = Trie()
    for w, freq in load_words(limit, path):
        t.add(w, freq=freq)
    return t


@lru_cache(maxsize=8)
def load_vocab(limit=None, path=None):
    """Cached word list, for brute-force reference scans."""
    return [w for w, _ in load_words(limit, path)]
