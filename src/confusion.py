import os
import pandas as pd

class Confusion:
    def __init__(self, data_dir="data"):
        self.tables = {}
        
        for name in ["del", "rev", "add", "subst"]:
            path = os.path.join(data_dir, f"{name}.csv")
            if os.path.exists(path):
                self.tables[name] = pd.read_csv(path, index_col=0)
            else:
                self.tables[name] = None
                print(f"Warning: {name}.csv not found")

    def _get_val(self, table_name, x, y):
        df = self.tables.get(table_name)
        if df is not None and x in df.index and y in df.columns:
            return df.loc[x, y]
        return 0.0

    def get_del(self, x, y):
        return self._get_val("del", x, y)

    def get_rev(self, x, y):
        return self._get_val("rev", x, y)

    def get_add(self, x, y):
        return self._get_val("add", x, y)

    def get_subst(self, x, y):
        return self._get_val("subst", x, y)
