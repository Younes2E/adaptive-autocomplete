# Journal — autocomplétion tolérante aux fautes sur Trie (JITA 2026)

Dernière mise à jour : 6 septembre 2026. Deadline soumission : 9 septembre 2026 (3 jours).

État du dépôt : commit `4d1c0f9`, arbre propre, gate de correction **17/17 tests
verts** (vérifié à l'instant sur ce commit).

---

## 1. Ce qui a été fait

### La tâche, précisée
Pas de la correction orthographique classique : de l'**autocomplétion tolérante
aux fautes**. Étant donné une requête `q` et un rayon `k`, retourner les mots
`w` du dictionnaire tels qu'**il existe un préfixe `p` de `w` avec OSA(q,p) ≤ k**.
Argument central du papier : pour la correction seule, le Trie n'est qu'une
optimisation ; pour correction + complétion, la baseline doit énumérer toutes
les variantes *puis* toutes leurs complétions — le Trie devient structurellement
nécessaire, pas seulement plus rapide.

### Code écrit
- **`src/trie.py::search_dp`** — le cœur. Un parcours unique du Trie porte une
  ligne DP OSA par branche ; émission en bloc dès qu'un nœud matche (tout son
  sous-arbre devient complétions valides sans DP supplémentaire) ; élagage dès
  que `min(ligne) > k`. `get_noise()` **gelée intacte**, gardée comme 3ᵉ point
  de comparaison (« récursion naïve »).
- **`src/baseline.py`** — génération-puis-lookup (Kernighan §2), avec filtre
  OSA en sortie (composer `edits1` deux fois atteint la distance OSA 3, ex.
  `rf→for`, sans quoi la baseline renverrait un sur-ensemble).
- **`src/reference.py`** — référence brute-force **en double implémentation**
  indépendante, pour éviter un gate circulaire (voir §3).
- **`src/utils.py`** — `osa_row` factorisée une seule fois ; `softmax` corrigée
  (débordait en `nan` à partir de quelques milliers de candidats).
- **`src/confusion.py`** — chemin relatif au dépôt (marchait avant seulement
  lancé depuis la racine) ; valeurs mises en cache (pandas `.at` ~1-3 µs/appel,
  dominerait le temps de recherche mesuré).
- **`tests/test_correctness.py`** — gate obligatoire en 7 couches (L0 à L7,
  détail en §3). Doit passer avant tout benchmark.
- **`scripts/`** : `benchmark.py` (latence + nœuds visités + throughput),
  `evaluate.py` (recall/top-k/MRR ventilés par longueur de préfixe),
  `fetch_data.py`, `get_noise_recall.py`, `make_figures.py`.
- **`run_all.py`** — reproductibilité en une commande (gate → benchmark →
  évaluation → figures → manifest avec seed/versions/SHA git).

### Bugs trouvés et corrigés
1. **Transposition OSA désactivée à la profondeur 2** : la règle utilisait la
   ligne du parent au lieu du grand-parent, gardée sur la mauvaise variable.
   Ratait silencieusement `hte→the`, `acr→car`. Trouvé par le gate (couche L1),
   pas par relecture.
2. **Labels de canal partagés dans un sous-arbre émis** : le mot exact tapé
   (`then→then`) héritait de l'alignement du préfixe émetteur et recevait
   `op=ins` au lieu de `op=None` — scoré comme une faute (0.9 → 5e-5) au lieu
   du score du mot correct. Deux correctifs ont été nécessaires (le premier a
   réparé ce cas et cassé les complétions propres du type `ann→anna`) avant
   d'arriver à `_best_prefix_op` : label recalculé exactement par mot via
   `osa_row`, figé par la couche **L7** du gate (`op=None ⇔ q est un préfixe
   exact du mot`). A changé les chiffres d'accuracy (top-1 à `|q|=4` :
   7.5 % → 35 %) — les anciens chiffres étaient biaisés en faveur du mot exact.
3. **`sub.csv` lu à l'envers dans `editprob`** (code d'origine, non corrigé —
   voir §4).

### Corrections apportées à l'énoncé du problème (CLAUDE.md)
- `OSA("cra","ac") = 3`, pas 2. La conclusion tient (`access`/`act` sont bien
  atteints depuis `cra` à k=2) mais via le préfixe `a`, pas `ac`. Figé en test.
- `k ≥ |q|` est dégénéré : le préfixe vide matche toujours, donc `q="th"` à k=2
  retourne 100 % du dictionnaire (mesuré : 50000/50000). Deux contraintes de
  longueur envisagées ont été testées et rejetées. Règle retenue : n'évaluer
  que les cellules `k < |q|`.

---

## 2. Résultats mesurés

### Performance (Table 1, k=2, run le plus récent)
Gain croissant avec la longueur du préfixe à dico fixe (10k : 16×→164× de
`|q|`=3 à 7 ; 50k : 4×→54×) : la baseline énumère variantes×complétions et
explose, `search_dp` reste quasi plat. Gain décroissant avec la taille du
dictionnaire à `|q|` fixe (10k→100k : 61×→13×) : coûts orthogonaux — la
baseline dépend de la longueur de requête, `search_dp` de la densité du trie.
OOM baseline à 333k (index préfixe plafonné à 100k mots) — publiable en soi.
**Ce run a tourné en concurrence d'autres calculs sur la machine : facteurs de
gain fiables, valeurs absolues ~2× hautes. À refaire au calme avant table
finale — voir §5.**

### Qualité (testset1, dico 20k, ventilé par |q| comme demandé)
Recall ~100 % dès 2 caractères (la recherche trouve toujours le bon mot) ;
top-1 monte de 0-3 % à `|q|`=2 jusqu'à 52-60 % à `|q|`=6-7 (dépend du nombre de
candidats à départager, 3880→1). `get_noise` : précision 100 %, recall
43-89 % selon la longueur — jamais de faux positif, mais rate souvent le bon
mot sur préfixe court.

Détail complet, tables et figures : `RESULTS.md`.

---

## 3. Le gate de correction — pourquoi 7 couches et pas 4

- **L0 anti-circularité** : la référence et `search_dp` partagent le même
  lemme (« dernière ligne DP = distances à tous les préfixes »). Si le lemme
  était faux, les deux seraient faux à l'identique et tout passerait à vide.
  Vérifié sur 3000 paires aléatoires contre une énumération naïve indépendante.
- **L1** régressions nommées (`hte→the`, `acr→car`, `cra→{access,act}`).
- **L2/L3** égalité exacte d'ensembles vs force brute, exhaustif à 20k/50k.
- **L4** échantillonné à 100k/333k.
- **L5** `search_dp == baseline`.
- **L6** `get_noise` gelée (signature + sortie).
- **L7** sémantique des labels de canal, ajoutée après le bug §1.2 — les
  couches L0-L6 ne comparent que les mots, jamais `(op,x,w)`.

---

## 4. Ce qui reste non résolu — décisions à prendre

### a. Orientation des matrices de confusion (code d'origine, non touché)
Vérifié dans `references/published_1990_coling.pdf` : `sub.csv` est une copie
verbatim de la table du papier (ligne = tapé, colonne = correct — confirmé
caractère pour caractère sur la ligne `a`). `editprob()` dans
`noisy_channel.py` lit `substitute(correct, tapé)`, donc lit la matrice
**transposée** avec le mauvais dénominateur. `get_noise()` a aussi une
divergence sur `rev` (bigramme tapé vs bigramme correct attendu par le papier).
**Décision à prendre** : corriger `noisy_channel.py`, ou
documenter l'écart dans le papier et le garder tel quel (les deux générateurs
de candidats sont affectés pareil, donc la comparaison n'en souffre pas — seule
la table d'accuracy absolue serait légèrement fausse).

### b. Traçabilité des matrices
`count_unigram.csv`/`count_bigram.csv` : reproductibles (`train/n-grams.py`,
corpus Brown/NLTK). `del.csv`/`insert.csv`/`rev.csv`/`sub.csv` : ajoutées à la
main (commit `a59b1d6`), pas de script. Seule la ligne `a` de `sub.csv` a été
vérifiée mot pour mot contre le PDF. **À faire si le papier les cite comme
« Kernighan et al. 1990 » sans réserve** : vérifier les 3 autres matrices
ligne à ligne (§5).

### c. Provenance de `en_freq.txt`
Format et contenu correspondent à `count_1w.txt` de Norvig, mais rien dans ce
dépôt (script, commit) ne le prouve — c'est une affirmation non vérifiée par
moi. Sans conséquence pour les résultats, seulement pour la citation exacte
dans le papier.

---

## 5. Ce qu'on va faire (3 jours restants)

Par ordre de priorité pour un extended abstract de 3 pages :

1. **Relancer le benchmark seul, machine au repos** (`python scripts/benchmark.py`)
   pour une table 1/2 finale sans bruit de contention — actuellement à ~2× de
   ce qu'elles devraient être en valeur absolue.
2. **Décider du point 4a** (matrices de confusion) : corriger ou documenter.
   Affecte la table d'accuracy absolue, pas la comparaison search_dp/baseline.
3. **Vérifier `del.csv`/`insert.csv`/`rev.csv`** contre le PDF si elles doivent
   être citées sans réserve (point 4b) — sinon les citer avec la réserve
   « recopiées, non vérifiées intégralement ».
4. **Rédiger les 3 pages LNCS** : intro/motivation, related work (Kernighan
   1990, Church & Gale 1991, Brill & Moore 2000 — PDFs déjà dans `references/`),
   méthode (DP-sur-Trie OSA, émission de sous-arbre, élagage), setup
   expérimental, résultats (tables + `figures/fig_prefix_length.png` en figure
   principale), conclusion. Le contenu factuel est prêt dans `RESULTS.md` ;
   ce qui manque est la mise en forme LNCS et la prose.
5. **Corrections à porter dans le texte**, déjà identifiées : témoin de
   l'exemple `cra→ac` (c'est `cra→a`), règle de dégénérescence `k<|q|`,
   caveat OSA restreinte vs Damerau illimité (`osa("rf","for")=3`).
6. Soumission OpenReview.

---

## Reproduire

```bash
python tests/test_correctness.py     # doit sortir 0 avant toute autre étape
python run_all.py --quick            # gate + grille reduite
python run_all.py --full             # grille complete + gate 333k
```

Machine de référence pour les temps déjà mesurés : AMD64, Windows 11,
Python 3.12.6, numpy 2.4.3 / pandas 3.0.2 (voir `results/manifest.json` après
`run_all.py`).
