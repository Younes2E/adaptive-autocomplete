from trie import Trie
from confusion import Confusion
from noisy_channel import *

def main():
    trie = Trie()
    confusion = Confusion()
    trie.load_dict("data/dict/en_freq.txt")
    word = str(input("Enter a word : "))
    print(f"Autocomplete : {word}")
    print(noisy_channel(word, trie, confusion))
    print(len(trie.get_noise(word)))

if __name__ == "__main__":
    main()