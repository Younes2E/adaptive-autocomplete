import pandas as pd
import nltk
nltk.download('brown') 
from nltk.corpus import brown

alphabet = [chr(97+i) for i in range(26)]

df_bigram = pd.DataFrame(0, index=alphabet, columns=alphabet)
df_unigram = pd.Series(0, index = alphabet)

words = brown.words()

def main():
    print(type(words))

if __name__ == "__main__":
    main()