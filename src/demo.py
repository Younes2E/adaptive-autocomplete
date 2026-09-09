"""Demo interactive : tape un debut de mot (eventuellement faux), voir le top 5.

    python src/demo.py
"""
from pathlib import Path

from confusion import Confusion
from noisy_channel import noisy_channel
from trie import Trie
from utils import truncate_proba

DICT = Path(__file__).resolve().parent.parent / "data" / "dict" / "en_freq.txt"


def main():
    trie = Trie()
    trie.load_dict(DICT)
    confusion = Confusion()
    word = input("Enter a word : ").strip().lower()
    for c, prob in noisy_channel(word, trie, confusion, n=5):
        print(f"{c} : {truncate_proba(prob * 100)}%")


if __name__ == "__main__":
    main()
