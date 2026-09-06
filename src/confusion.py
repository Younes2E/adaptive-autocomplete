from pathlib import Path
import pandas as pd

# Relative to the repo root, not the caller's cwd, so scripts/ and tests/ work too.
MATRIX_DIR = Path(__file__).resolve().parent.parent / "data" / "matrices"

class Confusion:
    def __init__(self, base_path=MATRIX_DIR):
        # Values are read once per candidate during ranking. pandas .at costs
        # ~1-3 us a lookup, which at thousands of candidates would swamp the
        # search time this project measures, so keep plain dicts instead.
        self.tables = {}
        for name in ["del", "rev", "insert", "sub", "count_unigram", "count_bigram"]:
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
