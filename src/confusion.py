"""Tables de confusion de Kernighan, Church & Gale (COLING 1990).

Voir data/SOURCES.md pour la provenance des CSV. Les conventions d'indexation
(qui differe du papier pour `sub`) sont documentees dans RESULTS.md 4b et
volontairement conservees telles quelles.
"""
from pathlib import Path

import pandas as pd

# Relatif a la racine du depot, pas au cwd de l'appelant, pour que bench.py et
# demo.py marchent depuis n'importe ou.
MATRIX_DIR = Path(__file__).resolve().parent.parent / "data" / "matrices"

TABLES = ["del", "rev", "insert", "sub", "count_unigram", "count_bigram"]


class Confusion:
    def __init__(self, base_path=MATRIX_DIR):
        # Une valeur est lue par candidat pendant le scoring. pandas .at coute
        # ~1-3 us par acces, ce qui a plusieurs milliers de candidats dominerait
        # le temps de recherche que ce projet mesure : on aplatit en dict.
        self.tables = {}
        for name in TABLES:
            df = pd.read_csv(Path(base_path) / f"{name}.csv", index_col=0)
            self.tables[name] = {(r, c): float(df.at[r, c])
                                 for r in df.index for c in df.columns}

    def delete(self, x, y):
        return self.tables["del"][(x, y)]

    def reverse(self, x, y):
        return self.tables["rev"][(x, y)]

    def insert(self, x, y):
        return self.tables["insert"][(x, y)]

    def substitute(self, x, y):
        return self.tables["sub"][(x, y)]

    def count_unigram(self, x):
        return self.tables["count_unigram"][(x, "count")]

    def count_bigram(self, x, y):
        return self.tables["count_bigram"][(x, y)]
