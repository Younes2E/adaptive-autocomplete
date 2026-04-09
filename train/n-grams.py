import pandas as pd
from nltk.corpus import brown

def create_counts():
    alphabet = [chr(97+i) for i in range(26)]
    alpha_ext = alphabet + ['@']

    df_bigram = pd.DataFrame(0, index=alpha_ext, columns=alphabet)
    df_unigram = pd.Series(0, index=alpha_ext)

    for word in brown.words():
        word = word.lower()
        
        if word and all(c in alphabet for c in word):
            df_unigram['@'] += 1
            for char in word:
                df_unigram[char] += 1
                
            df_bigram.at['@', word[0]] += 1
            for i in range(len(word) - 1):
                w_prev = word[i]
                w_curr = word[i+1]
                df_bigram.at[w_prev, w_curr] += 1

    return df_unigram, df_bigram

def main():
    df_unigram, df_bigram = create_counts()
    df_unigram.to_csv("data/matrices/count_unigram.csv", index_label="char", header=["count"])
    df_bigram.to_csv("data/matrices/count_bigram.csv")

if __name__ == "__main__":
    main()