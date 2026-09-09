# Journal — autocomplétion tolérante aux fautes sur Trie (JITA 2026)

Dernière mise à jour : 9 septembre 2026 (jour de la deadline).

État du dépôt : tout le pipeline tient dans **`bench.py`** (correction →
rappel/précision → temps CPU) ; gate de correction vert, benchmark relancé sur
machine au repos. Tables courantes : `results/bench.txt`, `results/benchmark.csv`,
`results/quality.csv`.

> **Note de lecture.** Le commit `bcfbfd7` a regroupé `run_all.py`, `tests/` et
> `scripts/` dans `bench.py`, et fusionné `search_dp` dans `get_noise` : la
> récursion naïve d'origine n'existe plus, `get_noise` **est** la recherche DP.
> Les sections ci-dessous qui parlent de `search_dp` désignent donc `get_noise`.

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
- **`src/trie.py::get_noise`** — le cœur. Un parcours unique du Trie porte une
  ligne DP OSA par branche ; émission en bloc dès qu'un nœud matche (tout son
  sous-arbre devient complétions valides sans DP supplémentaire) ; élagage dès
  que `min(ligne) > k`.
- **`src/baseline.py`** — génération-puis-lookup (Kernighan §2), avec filtre
  OSA en sortie (composer `edits1` deux fois atteint la distance OSA 3, ex.
  `rf→for`, sans quoi la baseline renverrait un sur-ensemble).
- **`bench.py::reference`** — référence brute-force indépendante (« un préfixe
  de `w` est à distance ≤ k »), volontairement lente, qui sert de vérité terrain.
- **`src/utils.py`** — `osa_row` factorisée une seule fois ; `softmax` corrigée
  (débordait en `nan` à partir de quelques milliers de candidats).
- **`src/confusion.py`** — chemin relatif au dépôt (marchait avant seulement
  lancé depuis la racine) ; valeurs mises en cache (pandas `.at` ~1-3 µs/appel,
  dominerait le temps de recherche mesuré).
- **`bench.py`** — les trois sections en un fichier, dans cet ordre : la
  correction s'arrête au premier écart, donc aucun chiffre n'est produit sur du
  code faux. Écrit aussi les tables en CSV.

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

### Performance (k=2, run final sur machine au repos)
Gain croissant avec la longueur du préfixe à dico fixe (10k : 7×→139× de
`|q|`=3 à 7 ; 50k : 1×→48×) : la baseline énumère variantes×complétions et
explose (14 352→70 184 chaînes), tandis que `get_noise` visite *moins* de nœuds
quand la requête s'allonge (5 776→3 754) — l'élagage mord plus tôt. Gain
décroissant avec la taille du dictionnaire à `|q|` fixe (10k→100k : 51×→12×) :
coûts orthogonaux — la baseline dépend de la longueur de requête, `get_noise` de
la densité du trie. OOM baseline à 333k (index préfixe plafonné à 100k mots) —
publiable en soi.

**À k=1 la baseline nous bat** (jusqu'à 5-10× sur préfixe court et gros
dictionnaire) : elle n'énumère que 182 à 390 chaînes, trop peu pour que le
parcours du trie se rentabilise. Le régime de la contribution est donc : rayon
≥ 2, ou dictionnaire trop gros pour un index préfixe. Table 3 de `RESULTS.md`.

Les compteurs de travail (nœuds visités, chaînes générées) sont identiques au
chiffre près à ceux du run Windows précédent : seules les ms ont changé.

### Qualité (testset1, dico 50k, ventilé par |q|)
Rappel de 23 % (|q|=3) à 93 % (|q|=7) à k=2, et 100 % sur la faute entière.
**Le point à retenir : rappel et précision sont identiques à ceux de la baseline
sur les douze cellules** — le gain de vitesse ne coûte rien en qualité, les deux
implémentations rendent le même ensemble. Les métriques de classement
(top-k, MRR) venaient de `scripts/evaluate.py`, supprimé : à réécrire si le
papier les cite.

Détail complet, tables et figures : `RESULTS.md`.

---

## 3. Le gate de correction (`bench.py`, section 1)

Quatre vérifications, sur un dictionnaire de 20k mots :

- **lemme des préfixes (anti-circularité)** — `osa_row(a,b)[j] == OSA(a, b[:j])`
  pour tout `j`, sur 3000 paires tirées dans un alphabet réduit à 6 lettres
  (plus de collisions et de transpositions par tirage), contre `osa_recursive`,
  une implémentation OSA top-down écrite séparément. `get_noise` émet quand la
  cellule `n` de sa ligne courante passe sous le rayon, et `reference` filtre sur
  `min(osa_row(...))` : les deux reposent sur ce lemme, donc s'il était faux ils
  seraient faux à l'identique et l'égalité d'ensembles ci-dessous passerait à
  vide. Ce que le test n'établit pas : la récurrence OSA elle-même, partagée par
  les deux implémentations.
- **cas nommés** — les régressions qui ont été fausses un jour : `hte→the`,
  `acr→car` (transpositions), `cra→{access,act}`.
- **étiquettes du canal** — `op is None ⇔ la requête est un préfixe exact du
  mot`. Ajoutée après le bug §1.2 : la comparaison d'ensembles ne regarde que
  les mots, jamais `(op,x,w)`, et un bug y est passé.
- **égalité d'ensembles** — `get_noise == force brute == baseline` sur 40
  requêtes (|q| ∈ {3..7} × k ∈ {1,2}, moitié préfixes propres, moitié fautés).

Le pouvoir discriminant du test du lemme a été vérifié par mutation : sur trois
versions cassées de `osa_row` — transposition lue sur la ligne du parent (le bug
historique), transposition supprimée, et une ligne dont seule la dernière
cellule est juste — les trois sont détectées, la version correcte passe. C'est
la troisième qui compte : distance finale juste, lemme faux, exactement ce qu'une
comparaison contre une référence partageant le lemme laisserait passer.

Reste perdu au regroupement `bcfbfd7` : les vérifications échantillonnées à
**100k/333k**. Le gate valide donc l'implémentation à 20k ; les lignes 333k des
tables chronomètrent du code dont la correction n'est pas revérifiée à cette
taille (risque faible, l'algorithme ne branche pas sur la taille du dico).

---

## 3b. Deux résultats nouveaux du 9 septembre

### a. Le rappel annoncé venait du jeu de développement
`spell-testset1` est le jeu de *dev* de Norvig. `testset2` et `spell-errors`
étaient dans le dépôt depuis le début, jamais utilisés. Sur eux, le rappel à
|q|=7 (k=2) tombe de **83.3 % à 69.2 % et 54.4 %**, et sur le mot entier de
**98.3 % à 66.7 %**. Les deux jeux indépendants
s'accordent entre eux, et les intervalles de confiance à 95 % ne se recouvrent
pas — ce n'est pas du bruit. `bench.py --testset {testset1,testset2,errors}` ;
détail et table dans `RESULTS.md` §4.

### b. SymSpell est plus rapide que nous à la requête
La baseline « générer puis chercher » n'est pas l'état de l'art : SymSpell
(Garbe 2012) l'est. Implémenté dans `src/symspell.py`, adapté à la tâche
(on indexe chaque préfixe de chaque mot), complétude vérifiée contre la force
brute. Il est **3 à 39× plus rapide que `get_noise`** sur la latence de requête.

Ce qu'il paie, à 333k et k=2 : **22× la mémoire** (6.17 Go contre 0.28 Go),
**36× la construction** (20.7 s contre 0.57 s) et **125× la mise à jour**
(120 µs/mot contre 1 µs/mot) — et il n'a aucun équivalent de `Trie.type()`,
donc pas d'adaptation en ligne à la frappe, ce qui est le sujet même du projet.

**Conséquence pour le papier** : la thèse « on est 139× plus rapide » ne tient
pas face à l'état de l'art et doit devenir « SymSpell est plus rapide quand on
peut se payer son index ; le trie tient le dictionnaire complet dans un
vingtième de la mémoire, se construit en une demi-seconde et se met à jour en
ligne ». Plus étroit, mais défendable en review. Détail : `RESULTS.md` §5b.

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

## 5. Ce qu'on va faire (jour de la deadline)

Par ordre de priorité pour un extended abstract de 3 pages :

1. ~~Relancer le benchmark seul, machine au repos~~ — **fait** : tables 1 à 3 de
   `RESULTS.md`, sortie brute dans `results/bench.txt`, CSV dans
   `results/benchmark.csv` et `results/quality.csv`.
2. **Décider du point 4a** (matrices de confusion) : corriger ou documenter.
   Affecte la table de probabilités absolues, pas la comparaison
   `get_noise`/baseline. L'écart sur `rev` s'est résolu de lui-même en
   fusionnant la DP dans `get_noise` (voir RESULTS.md §4b) ; il ne reste que
   celui sur `sub`.
3. **Vérifier `del.csv`/`insert.csv`/`rev.csv`** contre le PDF si elles doivent
   être citées sans réserve (point 4b) — sinon les citer avec la réserve
   « recopiées, non vérifiées intégralement ».
4. **Rédiger les 3 pages LNCS** : intro/motivation, related work (Kernighan
   1990, Church & Gale 1991, Brill & Moore 2000 — PDFs déjà dans `references/`),
   méthode (DP-sur-Trie OSA, émission de sous-arbre, élagage), setup
   expérimental, résultats (tables 1 à 3 de `RESULTS.md` +
   `figures/fig_prefix_length.png` en figure principale, régénérée depuis le
   run final), conclusion. Le contenu factuel est prêt dans `RESULTS.md` ;
   ce qui manque est la mise en forme LNCS et la prose.
5. **Corrections à porter dans le texte**, déjà identifiées : témoin de
   l'exemple `cra→ac` (c'est `cra→a`), règle de dégénérescence `k<|q|`,
   caveat OSA restreinte vs Damerau illimité (`osa("rf","for")=3`).
6. Soumission OpenReview.

---

## Reproduire

```bash
python -m venv env && ./env/bin/pip install -r requirements.txt
./env/bin/python bench.py --skip quality bench      # gate seul, ~20 s
./env/bin/python bench.py --sizes 10000 --pairs 20  # passe rapide
./env/bin/python bench.py > results/bench.txt       # run complet, table finale
./env/bin/python make_figures.py                    # figures depuis le CSV
./env/bin/python src/demo.py                        # demo interactive
```

Le run complet écrit aussi `results/benchmark.csv` et `results/quality.csv`.
Machine du run courant : Apple Silicon (arm64), macOS, Python 3.14.5,
numpy 2.5.3 / pandas 3.0.5 — en-tête reproduit dans `results/bench.txt`.
