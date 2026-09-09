"""Baseline SymSpell (index de suppressions) adaptee a l'autocompletion.

C'est le concurrent serieux, celui qu'un relecteur citera : Garbe (2012),
generalement presente comme la methode la plus rapide pour la correction
approchee. Le principe : precalculer, pour chaque entree du dictionnaire, toutes
les chaines obtenues en supprimant jusqu'a k caracteres, et les indexer. A la
requete, on genere les memes suppressions de q (donc ~C(|q|,k) chaines, pas
54*|q|^2 comme la generation naive) et on intersecte.

Adaptation a NOTRE tache : un mot est une reponse des qu'UN de ses prefixes est
a distance <= k. L'entree indexee n'est donc pas le mot mais **chaque prefixe de
chaque mot** -- exactement l'ensemble des noeuds du trie, mais materialise a
plat, avec pour chacun toutes ses suppressions. C'est la ou se joue la
comparaison : SymSpell echange de la memoire de precalcul contre du temps de
requete, la ou le trie garde les prefixes factorises.

Verification de completude : la garantie de SymSpell est etablie pour la
distance de Levenshtein. Notre tache utilise OSA (transpositions). La
completude est donc verifiee empiriquement contre la force brute dans
bench.py, elle n'est pas supposee.
"""
from collections import defaultdict

from utils import osa


def deletes(word, k):
    """Toutes les chaines obtenues en supprimant jusqu'a k caracteres de `word`."""
    out = {word}
    frontier = {word}
    for _ in range(k):
        nxt = {w[:i] + w[i + 1:] for w in frontier for i in range(len(w))}
        out |= nxt
        frontier = nxt
    return out


def build_delete_index(words, k, max_depth=3):
    """(index suppressions -> prefixes, index prefixe -> mots, nb d'entrees).

    Le second index est celui de la baseline naive : une fois le prefixe
    identifie, il faut encore enumerer ses completions. Le cout de construction
    et la taille memoire des deux sont la vraie metrique de cette baseline.
    """
    delete_index = defaultdict(set)
    prefix_index = defaultdict(list)
    seen = set()
    for w in words:
        for i in range(len(w) + 1):
            prefix_index[w[:i]].append(w)
        for i in range(1, len(w) + 1):
            p = w[:i]
            if p in seen:                       # un prefixe partage n'est indexe qu'une fois
                continue
            seen.add(p)
            for d in deletes(p, k):
                delete_index[d].add(p)
    entries = sum(len(v) for v in delete_index.values())
    return dict(delete_index), dict(prefix_index), entries


def symspell_candidates(query, delete_index, prefix_index, k=1, max_depth=3):
    """Memes reponses que Trie.get_noise(query, k, max_depth), par index de suppressions.

    Retourne (ensemble de mots, nombre de prefixes candidats verifies).
    Le second chiffre est le travail de la requete, independant du materiel.
    """
    max_len = None if max_depth is None else len(query) + max_depth
    candidate_prefixes = set()
    for d in deletes(query, k):
        candidate_prefixes |= delete_index.get(d, frozenset())

    found = set()
    checked = 0
    for p in candidate_prefixes:
        checked += 1
        if osa(query, p) > k:                   # l'index sur-genere : on verifie
            continue
        for w in prefix_index.get(p, ()):
            if max_len is None or len(w) <= max_len:
                found.add(w)
    # Le prefixe vide n'est jamais indexe (il n'a pas de suppression propre) :
    # il matche des que k >= |query|, cas degenere ecarte par la tache (k < |q|).
    return found, checked
