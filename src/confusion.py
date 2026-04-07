import os
import pandas as pd

class Confusion:
    def __init__(self, data_dir="data"):
        self.tables = {}
        
        for name in ["del", "rev", "insert", "sub", "unigram", "bigram"]:
            path = os.path.join(data_dir, f"{name}.csv")
            if os.path.exists(path):
                self.tables[name] = pd.read_csv(path, index_col=0)
            else:
                raise ImportError(f"Erreur confusion : {name}")

    def delete(self, x, y):
        df = self.tables["del"]
        return df.at[x,y]

    def reverse(self, x, y):
        df = self.tables["rev"]
        return df.at[x,y]

    def insert(self, x, y):
        df = self.tables["insert"]
        return df.at[x,y]

    def substitute(self, x, y):
        df = self.tables["sub"]
        return df.at[x,y]
    
    def count_unigram(self, x):
        df = self.table["unigram"]
        return df.at[x]
    
    def count_bigram(self, x, y):
        df = self.table["bigram"]
        return df.at[x,y]
