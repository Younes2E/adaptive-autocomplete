from trie import Trie
from confusion import Confusion
from noisy_channel import *

def load_dict(trie, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                word = parts[0].lower()
                try:
                    frequency = int(parts[1])
                    trie.add(word, freq = frequency)
                except Exception:
                    continue
                    

def main():
    trie = Trie()
    confusion = Confusion()
    load_dict(trie, "data/dict/en_freq.txt")
    word = str(input("Enter a word : "))
    print(f"Autocomplete : {word}")
    print(noisy_channel(word, trie, confusion))

if __name__ == "__main__":
    main()