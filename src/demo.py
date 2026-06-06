from trie import Trie
from confusion import Confusion
from noisy_channel import *
from utils import truncate_proba

def main():
    trie = Trie()
    confusion = Confusion()
    trie.load_dict("data/dict/en_freq.txt")
    word = str(input("Enter a word : "))
    candidates = noisy_channel(word, trie, confusion, n = 5)
    for c, prob in candidates:
        p = truncate_proba(prob*100)
        print(f"{c} : {p}%")

if __name__ == "__main__":
    main()