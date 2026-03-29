import os
import urllib.request
import pandas as pd
import difflib

DATA_DIR = "data"
# Dataset: format "correct: misspelled1, misspelled2, ...\n"
URL = "https://norvig.com/ngrams/spell-errors.txt"
DATASET_FILE = os.path.join(DATA_DIR, "spell-errors.txt")

# We include standard alphabet plus French accents and a few punctuation marks
ALPHABET = list("abcdefghijklmnopqrstuvwxyzéàèçù- '")

def download_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(DATASET_FILE):
        print(f"Downloading {URL}...")
        urllib.request.urlretrieve(URL, DATASET_FILE)
        print("Download complete.")

def init_matrix():
    # Returns a DataFrame initialized to a very small number (1e-5) for Laplacian smoothing.
    # This prevents absolute Zero probabilities which break math later on!
    return pd.DataFrame(1e-5, index=ALPHABET, columns=ALPHABET)

def process_errors():
    del_df = init_matrix()
    add_df = init_matrix()
    subst_df = init_matrix()
    rev_df = init_matrix()
    
    with open(DATASET_FILE, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        
    for line in lines:
        if ':' not in line:
            continue
        correct, misspellings = line.strip().split(':', 1)
        correct = correct.strip().lower()
        
        for miss in misspellings.split(','):
            miss = miss.strip().lower()
            
            # Skip if either word has characters we don't care about (like weird symbols)
            if not all(c in ALPHABET for c in correct + miss):
                continue
            
            # Use SequenceMatcher to find the exact edit that was made
            sm = difflib.SequenceMatcher(None, correct, miss)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    continue
                    
                # 1. Transposition (Reversal) -> e.g. 'the' vs 'teh'
                if tag == 'replace' and i2-i1 == 2 and j2-j1 == 2:
                    if correct[i1:i2] == miss[j1:j2][::-1]:
                        x, y = correct[i1], correct[i1+1]
                        rev_df.at[x, y] += 1
                        continue
                        
                # 2. Substitution -> e.g. 'a' vs 's'
                if tag == 'replace' and i2-i1 == 1 and j2-j1 == 1:
                    x, y = correct[i1], miss[j1]
                    subst_df.at[x, y] += 1
                    continue
                    
                # 3. Deletion -> e.g. missed a letter
                if tag == 'delete' and i2-i1 == 1:
                    # We track what character (x) preceded the deleted character (y)
                    x = correct[i1-1] if i1 > 0 else ' '
                    y = correct[i1]
                    if x in ALPHABET:
                        del_df.at[x, y] += 1
                    continue
                    
                # 4. Insertion -> e.g. added an extra letter
                if tag == 'insert' and j2-j1 == 1:
                    # We track what character (x) preceded the accidentally added character (y)
                    x = correct[i1-1] if i1 > 0 else ' '
                    y = miss[j1]
                    if x in ALPHABET:
                        add_df.at[x, y] += 1
                    continue

    return del_df, add_df, subst_df, rev_df

def normalize(df):
    # Convert absolute counts to probabilities by making each row sum to 1.0
    return df.div(df.sum(axis=1), axis=0)

if __name__ == "__main__":
    download_data()
    print("Processing error data...")
    del_df, add_df, subst_df, rev_df = process_errors()
    
    print("Converting counts to probabilities (row-normalized)...")
    del_df = normalize(del_df)
    add_df = normalize(add_df)
    subst_df = normalize(subst_df)
    rev_df = normalize(rev_df)
    
    print("Saving to CSV...")
    del_df.to_csv(os.path.join(DATA_DIR, "del.csv"))
    add_df.to_csv(os.path.join(DATA_DIR, "add.csv"))
    subst_df.to_csv(os.path.join(DATA_DIR, "subst.csv"))
    rev_df.to_csv(os.path.join(DATA_DIR, "rev.csv"))
    print("Success! The 4 matrices (with special characters and probabilities) are ready.")
