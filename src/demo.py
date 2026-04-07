import json
import os
from trie import Trie
from confusion import Confusion
from noisy_channel import *




import csv

def load_unigrams(trie, file_path):
    """
    Lit le fichier CSV et ajoute chaque mot avec sa fréquence dans le Trie.
    """
    print(f"Chargement des données depuis {file_path}...")
    
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = str(row['word'])
            try:
                freq = int(row['count'])
                if word:
                    trie.add(word, freq)
            except (ValueError, TypeError):
                continue
    print(f"Chargement terminé. Total typed : {trie.nb_typed}")


def main():
    trie = Trie()
    load_unigrams(trie, "data/en_freq.txt")
    

if __name__ == "__main__":
    main()