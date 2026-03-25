# Adaptive Autocomplete - Implementation Plan

## Overview
An adaptive autocomplete system in Python that combines:
1. **Trie** for fast prefix-based word retrieval
2. **Noisy Channel Model** (Damerau-Levenshtein + confusion matrices) for spelling correction
3. **Language Model** for contextual word ranking
4. **Continual Learning** - the system adapts to the user over time

All in English, using public resources, pure Python + numpy.

---

## Architecture

```
User input (prefix or misspelled word)
        │
        ▼
   ┌─────────┐
   │  Trie   │ ── prefix candidates (fast lookup)
   └────┬────┘
        │
        ▼
┌───────────────┐
│ Noisy Channel │ ── edit distance candidates (Damerau-Levenshtein)
│  + Confusion  │    scored by P(x|w) from confusion matrices
│   Matrices    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│Language Model  │ ── P(w) or P(w|context) to rank candidates
│(n-gram, adapt.)│
└───────┬───────┘
        │
        ▼
  Ranked suggestions
```

---

## Step-by-step Implementation

### Step 1: `src/trie.py` — Trie Data Structure
As described in final.txt:
- **TrieNode**: `children`, `is_word`, `freq` (word frequency from corpus), `nb_used` (how many times the user selected this word)
- **Trie class**:
  - `add(word, freq)` — insert a word with its corpus frequency
  - `remove(word)` — remove a word
  - `use(word)` — increment `nb_used` when the user picks a word (continual learning)
  - `search(word)` → bool — check if word exists
  - `get(prefix, n, max_depth)` — return top-n words from the subtree under `prefix`, limited by depth, ranked by `freq + nb_used`
  - `save(path)` / `load(path)` — JSON serialization for session persistence

### Step 2: `src/edit_distance.py` — Damerau-Levenshtein + Candidate Generation
- `damerau_levenshtein(s1, s2)` — compute weighted edit distance using confusion matrices
- `generate_candidates(word, trie, max_dist=2)` — find all words in the trie within edit distance ≤ max_dist
  - Uses the technique from the PDF: generate all strings at edit distance 1 (insertions, deletions, substitutions, transpositions), check which are in the trie, then repeat for distance 2

### Step 3: `src/noisy_channel.py` — Noisy Channel Spelling Correction
Following Jurafsky Ch. D:
- **Confusion matrices** (26×26): `del[x,y]`, `ins[x,y]`, `sub[x,y]`, `trans[x,y]`
  - Initialized from Peter Norvig's public error counts or from a public misspelling corpus
- `channel_probability(typo, candidate)` — P(x|w) using Eq. D.6 from the PDF
- `correct(word, trie, language_model, n=5)` — apply the noisy channel formula:
  `ŵ = argmax P(x|w) · P(w)^λ` and return top-n candidates

### Step 4: `src/language_model.py` — N-gram Language Model with Continual Learning
- Train on a public English corpus (e.g., Wikipedia dump from HuggingFace `datasets`, or a smaller corpus like Brown/Reuters from NLTK)
- **Unigram + Bigram + Trigram** with Stupid Backoff (simple, efficient)
- `P(word)` — unigram prior
- `P(word | context)` — bigram/trigram probability given previous words
- **Continual learning**: when the user types text, update n-gram counts incrementally
- Save/load model state to JSON

### Step 5: `src/autocomplete.py` — Main Autocomplete Engine
Combines all components:
- `suggest(prefix, context, n=5)`:
  1. Get prefix matches from the Trie (`trie.get`)
  2. If the prefix is not in the dictionary, run noisy channel correction
  3. Score all candidates using: `score = log P(x|w) + λ · log P(w|context) + μ · log(1 + nb_used)`
  4. Return top-n ranked suggestions
- `feed(text)` — user confirms a word: update trie (`use`), update language model counts
- `add_to_dictionary(text)` — scan text, add words + occurrence counts to trie
- `save_session()` / `load_session()` — persist trie + LM state to JSON

### Step 6: `src/demo.py` — Interactive CLI Demo
- Simple REPL where the user types words/sentences
- Shows autocomplete suggestions in real-time
- User can accept a suggestion (feeds back into the system)
- Demonstrates continual learning across the session

---

## Public Data Sources
- **Dictionary/word frequencies**: Peter Norvig's `count_1w.txt` (~1/3 million word frequency list) — downloadable
- **Confusion matrices**: Norvig's spelling error data or Birkbeck corpus (Roger Mitton)
- **Language model training**: NLTK Brown corpus, or HuggingFace `wikipedia` dataset (small subset)
- **Misspelling test data**: Birkbeck corpus or Norvig's `spell-testset1.txt`

## Dependencies
- `numpy` (already in requirements.txt)
- `nltk` (for Brown corpus / tokenization) — to add
- Optional: `datasets` (HuggingFace) if we want Wikipedia data
