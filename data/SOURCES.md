# Provenance des donnees

Chaque fichier a ete compare a sa source (md5 apres normalisation des fins de
ligne) le 6 septembre 2026 : identiques.

| fichier | source | md5 |
|---|---|---|
| `dict/en_freq.txt` | https://norvig.com/ngrams/count_1w.txt — 333 333 mots avec frequences, Google Web Trillion Word Corpus (Norvig, *Natural Language Corpus Data*, in *Beautiful Data*, 2009) | `1710e1aa36917a32ba8cee42acf8af4f` |
| `test/spell-errors.txt` | https://norvig.com/ngrams/spell-errors.txt — 7 841 lignes, fautes issues de Wikipedia et du corpus Birkbeck de Roger Mitton | `ee85b431c25f683819ac66a846282c9c` |
| `test/spell-testset1.txt` | https://norvig.com/spell-testset1.txt — jeu de developpement de Norvig, *How to Write a Spelling Corrector*, corpus Birkbeck (Mitton) | `5af08a3c69fe1489d836000fb630041f` |
| `test/spell-testset2.txt` | https://norvig.com/spell-testset2.txt — jeu de test final du meme article | `5c80028607c9b66c6baca826323f9c2f` |

Format des jeux de test : `correct: faute1 faute2 ...` (espaces) ; `spell-errors.txt`
separe par des virgules et peut suffixer `*N` (nombre d'occurrences).

Verification : `md5sum` apres `tr -d '\r'`, ou

    curl -sL https://norvig.com/ngrams/count_1w.txt | tr -d '\r' | md5sum

## Matrices de confusion (`matrices/`)

- `del.csv`, `insert.csv`, `rev.csv`, `sub.csv` : recopiees a la main depuis les
  tables de Kernighan, Church & Gale, *A Spelling Correction Program Based on a
  Noisy Channel Model* (COLING 1990). Seule la ligne `a` de `sub.csv` a ete
  verifiee caractere par caractere contre le PDF ; les autres lignes et les
  trois autres matrices ne l'ont pas ete.
- `count_unigram.csv`, `count_bigram.csv` : comptages de caracteres sur le
  corpus Brown (NLTK), reproductibles avec `train/n-grams.py`.
