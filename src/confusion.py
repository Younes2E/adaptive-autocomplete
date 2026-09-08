import os
import pandas as pd

class Confusion:
    def __init__(self):
        self.tables = {}
        
        for name in ["del", "rev", "insert", "sub", "count_unigram", "count_bigram"]:
            self.tables[name] = pd.read_csv(f"data/matrices/{name}.csv", index_col=0)

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
        df = self.tables["count_unigram"]
        return df.at[x, "count"]
    
    def count_bigram(self, x, y):
        df = self.tables["count_bigram"]
        return df.at[x,y]

