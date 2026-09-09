# Ce qui a été fait le 9 septembre 2026 — et pourquoi ça change le papier

Document de passation. Il explique les décisions, pas seulement les commandes.
Les tables complètes sont dans `RESULTS.md`, l'historique dans `JOURNAL.md`.

---

## En une phrase

La thèse « notre trie est 139× plus rapide » **ne tient pas** face à l'état de
l'art : SymSpell répond 3 à 39× plus vite que nous. Ce qui tient, mesures à
l'appui, c'est que le trie fait la même chose avec **22× moins de mémoire**,
**36× moins de construction** et **125× moins cher à la mise à jour**. Et le
rappel qu'on annonçait venait du jeu de développement : sur des données tenues
à l'écart, il tombe de 83 % à 54 % sur préfixe de 7, et de 98 % à 67 % sur le
mot entier.

Les deux points sont désagréables. Les deux valent mieux découverts maintenant
qu'en review.

---

## 1. Le résultat qui change l'argument : SymSpell

### Ce qui n'allait pas

Le papier comparait `get_noise` à une baseline « générer toutes les variantes
puis chercher » (Norvig / Kernighan). C'est la méthode pédagogique classique,
**ce n'est pas l'état de l'art**. La référence en correction approchée rapide
est SymSpell (Garbe, 2012) : on précalcule, pour chaque entrée du dictionnaire,
toutes les chaînes obtenues en supprimant jusqu'à `k` caractères, et on les
indexe. À la requête on génère les mêmes suppressions de `q` et on intersecte.

Battre la génération naïve est attendu. Un relecteur du domaine demandera
SymSpell.

### Ce qu'on a fait

`src/symspell.py` l'implémente, adapté à **notre** tâche : un mot est une
réponse dès qu'un de ses préfixes est à distance ≤ k, donc l'entrée indexée
n'est pas le mot mais **chaque préfixe de chaque mot**.

Complétude **vérifiée**, pas supposée : la garantie de SymSpell est établie
pour la distance de Levenshtein, or notre tâche utilise OSA (avec
transpositions). On a donc comparé ses réponses à la force brute à k=1 et k=2
sur 10k mots — égalité exacte. Sans cette vérification on aurait comparé nos
temps à ceux d'une méthode qui ne répond pas à la même question.

### Ce que ça donne

**Latence de requête — SymSpell gagne :**

| dico | k | \|q\| | get_noise | SymSpell | |
|---|---|---|---|---|---|
| 10k | 2 | 7 | 3.15 ms | 0.08 ms | 39× plus rapide |
| 100k | 2 | 3 | 38.78 ms | 7.67 ms | 5× |
| 100k | 2 | 7 | 16.15 ms | 0.45 ms | 36× |
| 333k | 2 | 7 | 33.60 ms | 1.07 ms | 31× |

**Ce qu'il paie pour ça (333k mots, k=2) :**

| | mémoire | construction | mise à jour |
|---|---|---|---|
| **trie** | **0.28 Go** | **0.57 s** | **1 µs / mot** |
| SymSpell | 6.17 Go (27 961 910 entrées) | 20.7 s | 120 µs / mot |
| rapport | **22×** | **36×** | **125×** |

Mesuré, pas estimé : chaque structure dans un processus neuf (`bench_memory.py`),
parce que `maxrss` est un maximum historique et que mesurer deux structures dans
le même processus donne le maximum de la plus grosse.

### Ce qu'il faut en conclure pour le papier

La bonne formulation n'est pas « on est plus rapide », c'est :

> SymSpell est plus rapide **quand on peut se payer son index**. Le trie tient
> le dictionnaire complet dans un vingtième de la mémoire, se construit en une
> demi-seconde, et se met à jour en ligne.

6 Go pour 333k mots disqualifie SymSpell sur un appareil contraint — or
l'autocomplétion tolérante aux fautes vit surtout sur des claviers mobiles.
C'est un positionnement plus étroit que celui qu'on avait, mais c'en est un qui
survit à une review.

**Et surtout** : le projet s'appelle *adaptive*-autocomplete. `Trie.add`,
`remove` et `type` maintiennent `freq` et `last_used` en O(|mot|) — le
dictionnaire s'adapte pendant que l'utilisateur tape (1000 `type()` en 1.2 ms).
L'index de suppressions n'a **aucun équivalent** : il ne porte pas de
fréquences, et insérer un mot coûte ~72 entrées d'index. C'est là que notre
structure est structurellement supérieure, pas sur la latence brute.

Figure : `figures/fig_tradeoff.png` (ce que la structure coûte / ce qu'elle rend).

---

## 2. Le rappel annoncé venait du jeu de développement

`data/test/` contient trois fichiers. Le benchmark n'utilisait que le premier,
**`spell-testset1`, qui est le jeu de *développement* de Norvig**. Les deux
autres étaient là depuis le début, jamais lus.

Rappel à k=2, dictionnaire 50k :

| \|q\| | testset1 (dev) | testset2 (held-out) | spell-errors (300 p.) |
|---|---|---|---|
| 3 | 21.7 % ±10.2 | 15.0 % ±9.0 | 26.6 % ±5.0 |
| 4 | 50.0 % ±12.3 | 20.7 % ±10.3 | 36.7 % ±5.5 |
| 5 | **78.2 % ±10.7** | 43.1 % ±12.4 | **41.8 % ±5.9** |
| 6 | 86.8 % ±9.1 | 53.6 % ±12.6 | 46.4 % ±6.3 |
| 7 | **83.3 % ±11.1** | 69.2 % ±12.2 | **54.4 % ±7.0** |
| mot entier | **98.3 % ±4.3** | 96.7 % ±5.2 | **66.7 % ±5.3** |

Les deux jeux indépendants s'accordent **entre eux** et pas avec testset1. À
|q|=5, |q|=7 et sur le mot entier, **les intervalles de confiance ne se
recouvrent pas** : l'écart n'est pas du bruit d'échantillonnage. Sur le mot
entier il fait 32 points. C'est la signature d'un jeu de dev qui flatte, que
quelqu'un ait ajusté dessus volontairement ou non.

`spell-errors` (36 564 paires exploitables) est le plus fiable par la taille de
son échantillon : ±5 à 7 points, contre ±9 à 13 pour les deux jeux à 60 paires.
Les intervalles sont ceux de Wilson à 95 %, choisis plutôt que l'approximation
normale parce qu'ils restent corrects près de 0 et de 1, où plusieurs cellules
se trouvent.

Les paires sont tirées au sort (seed 42), pas prises en tête de fichier — le
premier échantillonnage prenait les 60 premières lignes, ce qui sur un corpus
trié biaise le résultat.

**À faire dans le papier** : annoncer le rappel sur `spell-errors` ou
`testset2`, ou les trois côte à côte. Pas sur testset1 seul.

```bash
./env/bin/python bench.py --skip test bench symspell --testset errors --pairs 300
```

---

## 3. Ce qui reste vrai, et qui est un bon résultat

Sur les douze cellules et sur les trois jeux de test, **le rappel et la
précision de `get_noise` sont identiques à ceux de la baseline**. Le gain de
vitesse ne coûte rien en qualité : ce sont deux implémentations de la même
fonction, pas deux heuristiques. L'égalité des ensembles est en plus prouvée
requête par requête par le gate.

C'est la phrase à mettre juste à côté de la table de performance.

Reste également vrai, et c'est la partie élégante du papier : à k=2 les deux
coûts vont **dans des directions opposées**. La baseline énumère de plus en plus
de chaînes quand la requête s'allonge (14 352 → 70 184 de |q|=3 à 7), pendant
que `get_noise` visite de **moins en moins** de nœuds (5 776 → 3 754), parce que
l'élagage mord plus tôt. Ces deux compteurs sont indépendants du matériel — ils
sont sortis identiques au chiffre près sur Windows/Python 3.12 et sur
macOS/Python 3.14. C'est sur eux qu'il faut appuyer, pas sur les millisecondes.

Figure : `figures/fig_prefix_length.png`, panneau (b).

---

## 4. Fiabilité : ce qui a été vérifié

- **Lemme des préfixes restauré** (`bench.py`, section 1). `get_noise` et la
  référence brute-force reposent tous deux sur « la dernière ligne DP donne la
  distance à tous les préfixes ». Si ce lemme était faux, les deux seraient
  faux à l'identique et l'égalité d'ensembles passerait **sans rien prouver**.
  On le vérifie donc sur 3000 paires contre `osa_recursive`, une implémentation
  OSA écrite séparément.

  Son pouvoir de détection a été testé par mutation : trois versions cassées de
  `osa_row` (transposition lue sur la ligne du parent — le bug historique ;
  transposition supprimée ; ligne dont seule la dernière cellule est juste) sont
  **toutes détectées**, la version correcte passe. Le troisième cas est celui
  qui justifie la couche.

- **Correction vérifiée à l'échelle qu'on publie** (`--scale-check`) : égalité
  d'ensembles contre la force brute à **100k et 333k mots**, OK. Avant, les
  lignes 333k des tables chronométraient du code vérifié seulement à 20k.

- **Intervalles de confiance** sur toutes les cellules de rappel.

---

## 5. Nettoyage du code

- `src/confusion.py` : deux correctifs avaient été perdus lors du regroupement
  `bcfbfd7` et ont été ré-appliqués — chemin relatif au dépôt (marchait
  seulement lancé depuis la racine) et valeurs aplaties en dict. Le
  `pandas .at` par candidat coûte 1 à 3 µs, ce qui à plusieurs milliers de
  candidats domine le temps de recherche que le projet mesure. Valeurs
  identiques vérifiées (`sub[a,e]=342`, `count_bigram[a,n]=71278`).
- `src/trie.py` : suppression du `main()` de test qui faisait doublon avec
  `demo.py`. **Algorithme inchangé.**
- `src/noisy_channel.py` : docstring documentant l'écart assumé avec Kernighan,
  `distance` et `max_depth` devenus des paramètres, garde sur liste vide.
- `src/demo.py` : plus d'`import *`, chemin du dictionnaire relatif au dépôt.
- `results/legacy/` : les six fichiers produits par les scripts supprimés en
  `bcfbfd7` y sont rangés avec un README. Ils décrivent une API qui n'existe
  plus (`search_dp` d'un côté, `get_noise` récursif de l'autre) —
  `get_noise_recall.csv` compare notamment à une récursion naïve supprimée.
  **Ne pas les citer.**

Un écart avec Kernighan s'est résolu tout seul : `rev` étiquette maintenant avec
le bigramme du mot **correct**, conforme au papier (vérifié : `hte → the` rend
`("rev","t","h")`). Il ne reste que celui sur `sub` dans `editprob`, gelé par
décision.

---

## 6. Ce qui reste à décider

1. **Le trou principal : « adaptive » n'est pas mesuré.** `type()` et
   `last_used` existent, le ranker ne lit que `freq`, et aucune expérience ne
   montre que l'adaptation améliore quoi que ce soit. C'est une contribution
   réelle qui dort. Il faudrait un protocole en *session* (mots répétés, effets
   de récence), pas les paires isolées (faute → mot) actuelles.
2. **top-k / MRR** ne sont plus reproductibles (`scripts/evaluate.py` supprimé).
   Si le papier cite du classement, la métrique est à réécrire.
3. **`sub` dans `editprob`** : corriger ou documenter. N'affecte pas la
   comparaison, seulement les probabilités absolues.
4. **Provenance des matrices** : seule la ligne `a` de `sub.csv` a été vérifiée
   contre le PDF.

---

## 7. Tout reproduire

```bash
python -m venv env && ./env/bin/pip install -r requirements.txt

./env/bin/python bench.py --skip quality bench symspell   # gate seul
./env/bin/python bench.py --scale-check                   # + correction a 100k/333k
./env/bin/python bench.py --testset errors --pairs 300    # rappel fiable
./env/bin/python bench.py > results/bench.txt             # les 4 sections
./env/bin/python bench_memory.py                          # memoire trie vs SymSpell
./env/bin/python make_figures.py                          # figures depuis les CSV
./env/bin/python src/demo.py                              # demo interactive
```

Sorties : `results/bench.txt`, `results/benchmark.csv`, `results/symspell.csv`,
`results/memory.csv`, `results/quality_<jeu>.csv`, `figures/*.png`.

Machine des mesures : Apple Silicon (arm64), macOS, Python 3.14.5,
numpy 2.5.3 / pandas 3.0.5, seed 42.
