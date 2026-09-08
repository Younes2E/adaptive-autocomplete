"""Baseline naive : generer toutes les variantes, puis chercher (Norvig / Kernighan).

C'est l'approche classique a laquelle get_noise() est comparee. Pour la
correction seule elle est competitive. Pour l'autocompletion elle doit en plus
etendre chaque variante par toutes ses completions du dictionnaire : c'est ce
produit variantes x completions qui explose.
"""
from collections import defaultdict

from utils import osa

ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def edits1(word):
    """Toutes les chaines a une edition de `word` (del, transposition, sub, ins)."""
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in ALPHABET]
    inserts = [L + c + R for L, R in splits for c in ALPHABET]
    return set(deletes + transposes + replaces + inserts)


def variants(word, k):
    """(chaines a distance OSA <= k de `word`, nombre de chaines enumerees).

    Attention : composer edits1 deux fois atteint aussi des chaines a distance
    OSA 3 (ex. rf -> fr -> for, car OSA interdit de re-editer une sous-chaine
    transposee). Sans le filtre final la baseline renverrait un sur-ensemble.
    """
    out = {word}
    frontier = {word}
    for _ in range(k):
        frontier = {e for v in frontier for e in edits1(v)}
        out |= frontier
    # len(out) = nombre de chaines que la baseline a du enumerer avant tout
    # lookup : son cout reel, independant du materiel (~54n^2 pour k=2).
    return {v for v in out if osa(word, v) <= k}, len(out)


def build_prefix_index(words):
    """prefixe -> liste des mots qui commencent par ce prefixe.

    C'est l'index que la baseline DOIT construire pour repondre a la tache
    d'autocompletion. A 333k mots il ne tient plus en memoire.
    """
    index = defaultdict(list)
    for w in words:
        for i in range(len(w) + 1):
            index[w[:i]].append(w)
    return dict(index)


def naive_candidates(word, index, k=1, max_depth=3):
    """Memes reponses que Trie.get_noise(word, k, max_depth), par generation + lookup.

    Retourne (ensemble de mots, nombre de chaines enumerees avant lookup).
    Le second est la metrique d'explosion, independante du materiel.
    """
    max_len = None if max_depth is None else len(word) + max_depth
    vs, enumerated = variants(word, k)
    found = set()
    for v in vs:
        for w in index.get(v, ()):
            if max_len is None or len(w) <= max_len:
                found.add(w)
    return found, enumerated
