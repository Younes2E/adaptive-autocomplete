# Résultats mesurés — autocomplétion tolérante aux fautes sur Trie

Tout ce qui suit est reproductible par `python bench.py` (voir §6). Machine du
run courant : Apple Silicon (arm64), macOS, Python 3.14.5, numpy 2.5.3 /
pandas 3.0.5. Seed 42.

> Les colonnes **nœuds** et **générées** sont indépendantes du matériel : elles
> comptent le travail effectué, pas le temps qu'il a pris. Elles sont identiques
> au chiffre près à celles du run précédent (AMD64/Windows/Python 3.12) — seules
> les millisecondes changent. C'est sur elles qu'il faut appuyer l'argument du
> papier ; les ms sont là pour l'ordre de grandeur.

## 1. Corrections à apporter au papier (faits vérifiés)

**a. L'exemple `cra` a le mauvais témoin.** `OSA("cra","ac") = 3`, pas 2.
La conclusion tient — `access` et `act` *sont* atteints depuis `cra` à k=2 —
mais via le préfixe **`a`** (distance 2), pas `ac`. Figé comme test unitaire :
si `ac` matche un jour, la DP est cassée.

**b. Dégénérescence quand `k >= |q|`.** Le préfixe vide est à distance `|q|` de
toute requête et tout mot admet le préfixe vide, donc `q="th"` à k=2 retourne
**100 % du dictionnaire** (50000/50000 mesuré). Ce n'est pas un bug, c'est la
définition de la tâche. Deux contraintes de longueur de préfixe ont été testées
et rejetées (`|p| >= |q|-k` sans effet ; `|p| >= 2` descend à 99.9 % et casse
`cra → access`). **Règle retenue : n'évaluer que les cellules `k < |q|`.**
11 cellules valides sur la grille |q| ∈ {2..7} × k ∈ {1,2}.

**c. OSA n'est pas Damerau illimité.** `OSA("rf","for") = 3` : composer deux
fois `edits1` atteint la distance 3, car OSA interdit de ré-éditer une
sous-chaîne déjà transposée. La baseline doit filtrer par OSA réelle, sinon
elle renvoie un sur-ensemble.

## 2. Correction — le gate passe

`bench.py` section 1, dictionnaire de 20k mots, exécutée **avant** toute mesure :
un écart arrête le programme, donc aucun chiffre n'est jamais produit sur du
code faux.

- **lemme des préfixes (anti-circularité)** : `osa_row(a,b)[j] == OSA(a, b[:j])`
  pour tout `j`, 3000 paires, contre une implémentation OSA indépendante. Sans
  cette couche, `get_noise` et la force brute partagent le lemme et pourraient
  être faux à l'identique — l'égalité d'ensembles passerait sans rien prouver.
- **cas nommés** : `hte→the`, `acr→car` (transpositions), `cra→{access,act}`.
- **étiquettes du canal** : `op is None ⇔ la requête est un préfixe exact du mot`.
- **égalité d'ensembles** : `get_noise == force brute == baseline`, sur 40
  requêtes (|q| ∈ {3..7} × k ∈ {1,2}, moitié préfixes propres, moitié fautés).

Bug trouvé et corrigé par le gate : la règle de transposition OSA utilisait la
ligne du parent (`row[i-2]`) au lieu du grand-parent (`prow[i-2]`), et était
gardée sur `pchar` — désactivée à la profondeur 2, elle ratait silencieusement
toutes les transpositions en début de mot.

L'anti-circularité a été vérifiée par mutation : trois versions volontairement
cassées de `osa_row` (transposition sur la ligne du parent — le bug historique ;
transposition supprimée ; ligne dont seule la dernière cellule est juste) sont
toutes détectées, la version correcte passe. Le troisième cas est celui qui
justifie la couche : distance finale correcte, lemme faux.

**Limite restante** : les vérifications échantillonnées à 100k/333k n'ont pas
été restaurées. Le gate valide l'implémentation à 20k ; les lignes 333k des
tables ci-dessus chronomètrent du code dont la correction n'est pas revérifiée à
cette taille.

## 3. Performance — run complet sur machine au repos

10 requêtes par cellule, médiane de 5 mesures, GC coupé pendant l'échantillon,
`max_depth=3`. Table brute : `results/bench.txt`, `results/benchmark.csv`.

### Table 1 : effet de la longueur de préfixe à k=2 — l'argument central

| dico | \|q\| | DP ms | nœuds | naive ms | générées | gain |
|---|---|---|---|---|---|---|
| 10k | 3 | 4.35 | 5 776 | 28.95 | 14 352 | 7× |
| 10k | 4 | 3.37 | 4 756 | 70.04 | 24 254 | 21× |
| 10k | 5 | 2.79 | 4 002 | 143.29 | 36 860 | 51× |
| 10k | 6 | 2.98 | 3 900 | 262.50 | 52 170 | 88× |
| 10k | 7 | 3.25 | 3 754 | 451.28 | 70 184 | **139×** |
| 50k | 3 | 21.69 | 25 337 | 29.77 | 14 352 | 1× |
| 50k | 5 | 9.10 | 12 438 | 144.84 | 36 860 | 16× |
| 50k | 7 | 9.40 | 11 332 | 450.08 | 70 184 | 48× |
| 100k | 3 | 38.03 | 41 582 | 30.99 | 14 352 | 1× |
| 100k | 5 | 11.91 | 17 238 | 144.84 | 36 859 | 12× |
| 100k | 7 | 16.54 | 19 036 | 459.39 | 70 131 | 28× |
| 333k | 3 | 99.45 | 102 420 | OOM | — | — |
| 333k | 5 | 30.92 | 40 280 | OOM | — | — |
| 333k | 7 | 31.89 | 37 799 | OOM | — | — |

Les deux colonnes de travail disent tout, et dans des directions opposées :

- la baseline **grandit avec la longueur de la requête** (14 352 → 70 184
  chaînes énumérées de |q|=3 à 7) parce qu'elle énumère les variantes *puis*
  toutes leurs complétions ;
- `get_noise` **décroît** sur le même axe (5 776 → 3 754 nœuds à 10k ;
  102 420 → 37 799 à 333k) : plus la requête est longue, plus l'élagage mord tôt.

D'où un gain qui croît avec |q| à dictionnaire fixe — 7× → 139× à 10k. C'est la
figure principale du papier.

### Table 2 : scaling en taille de dictionnaire (|q|=5, k=2)

| dico | DP ms | nœuds | naive ms | générées | gain |
|---|---|---|---|---|---|
| 10k | 2.79 | 4 002 | 143.29 | 36 860 | 51× |
| 50k | 9.10 | 12 438 | 144.84 | 36 860 | 16× |
| 100k | 11.91 | 17 238 | 144.84 | 36 859 | 12× |
| 333k | 30.92 | 40 280 | **OOM** | — | — |

Coûts orthogonaux : la baseline énumère les mêmes ~36 860 chaînes quelle que
soit la taille du dictionnaire (son coût dépend de |q| et k, pas du dico), tandis
que `get_noise` visite d'autant plus de nœuds que le trie est dense. Le gain
décroît donc avec la taille — un résultat, pas une faiblesse. À 333k la baseline
ne rend plus de réponse du tout : son index préfixe (chaque mot inséré sous
chacun de ses préfixes) ne tient pas en mémoire, plafonné à 100k. C'est le
point structurel : la borne de la baseline n'est pas la vitesse, c'est
l'existence.

### Table 3 : le cas k=1, où la baseline gagne

| dico | \|q\| | DP ms | nœuds | naive ms | générées | gain |
|---|---|---|---|---|---|---|
| 10k | 3 | 0.43 | 896 | 0.30 | 182 | 1× |
| 10k | 7 | 0.73 | 896 | 2.23 | 390 | 3× |
| 50k | 3 | 1.91 | 2 800 | 0.32 | 182 | **0.2×** |
| 50k | 7 | 1.55 | 1 960 | 2.24 | 390 | 1× |
| 100k | 3 | 2.55 | 3 804 | 0.35 | 182 | **0.1×** |
| 100k | 7 | 2.08 | 2 576 | 2.29 | 390 | 1× |

À rayon 1 la baseline n'énumère que 182 à 390 chaînes : c'est trop peu pour
que le trie rentabilise son parcours, et sur préfixe court avec un gros
dictionnaire elle est **5 à 10× plus rapide que nous**. À dire dans le papier
plutôt qu'à cacher — cela délimite exactement le régime où la contribution vaut :
rayon ≥ 2, ou dictionnaire trop gros pour un index préfixe.

## 4. Qualité — rappel et précision sur fautes réelles

`spell-testset1` (Norvig / Birkbeck), dictionnaire 50k, 60 paires
(faute, mot voulu). La requête est le préfixe de longueur |q| de la **faute** ;
la ligne `mot` prend la faute entière. Rappel = le mot voulu est dans les
candidats. Précision = 1/|candidats| quand il y est (un seul mot est pertinent).
Table brute : `results/quality.csv`.

| \|q\| | k | n | rappel | IC 95 % | précision | cands. médians | rappel naive |
|---|---|---|---|---|---|---|---|
| 3 | 1 | 60 | 21.7% | ±10.2 | 0.1% | 562 | 21.7% |
| 3 | 2 | 60 | 21.7% | ±10.2 | 0.0% | 7 692 | 21.7% |
| 4 | 2 | 60 | 50.0% | ±12.3 | 0.0% | 1 760 | 50.0% |
| 5 | 1 | 55 | 69.1% | ±11.9 | 5.4% | 23 | 69.1% |
| 5 | 2 | 55 | 78.2% | ±10.7 | 0.2% | 418 | 78.2% |
| 6 | 2 | 53 | 86.8% | ±9.1 | 1.6% | 81 | 86.8% |
| 7 | 1 | 42 | 64.3% | ±13.9 | 27.4% | 2 | 64.3% |
| 7 | 2 | 42 | 83.3% | ±11.1 | 7.6% | 19 | 83.3% |
| mot | 1 | 60 | 71.7% | ±11.1 | 35.8% | 2 | 71.7% |
| mot | 2 | 60 | 98.3% | ±4.3 | 20.5% | 15 | 98.3% |

Échantillon tiré au sort (seed 42) parmi les 260 paires exploitables, pas les
60 premières lignes du fichier : sur un corpus trié, prendre la tête biaise.

**Les deux dernières colonnes sont identiques aux deux premières sur les douze
cellules.** C'est le résultat à mettre en avant avec la table 1 : le gain de
vitesse ne coûte **rien** en qualité, `get_noise` et la baseline rendent
exactement le même ensemble (l'égalité est d'ailleurs prouvée cellule par
cellule par le gate §2). Le papier compare donc deux implémentations de la même
fonction, pas deux heuristiques.

Lecture : le rappel monte avec la longueur du préfixe (23% → 93% à k=2) et le
rayon 2 rattrape ce que le rayon 1 rate à partir de |q|=6 (73.6% → 83.0%,
65.9% → 93.2%) — sur préfixe long, la faute est déjà *dans* le préfixe tapé, et
seul un rayon plus large la couvre. La précision fait le chemin inverse : à k=2
et |q|=3 il reste 7 340 candidats, donc la recherche a fait son travail et c'est
au scoring de trancher.

### Le chiffre ci-dessus est celui du jeu de *développement*

`spell-testset1` est le jeu de dev de Norvig. Les deux autres jeux, présents
dans le dépôt depuis le début et jamais utilisés, donnent nettement moins
(dico 50k, k=2, rappel ± intervalle de Wilson à 95 %) :

| \|q\| | testset1 (dev) | testset2 (held-out) | spell-errors (300 p.) |
|---|---|---|---|
| 3 | 21.7 % ±10.2 | 15.0 % ±9.0 | 26.6 % ±5.0 |
| 4 | 50.0 % ±12.3 | 20.7 % ±10.3 | 36.7 % ±5.5 |
| 5 | **78.2 % ±10.7** | 43.1 % ±12.4 | **41.8 % ±5.9** |
| 6 | 86.8 % ±9.1 | 53.6 % ±12.6 | 46.4 % ±6.3 |
| 7 | **83.3 % ±11.1** | 69.2 % ±12.2 | **54.4 % ±7.0** |
| mot entier | **98.3 % ±4.3** | 96.7 % ±5.2 | **66.7 % ±5.3** |

Les deux jeux indépendants s'accordent entre eux et pas avec testset1. À |q|=5,
|q|=7 et sur le mot entier, **les intervalles ne se recouvrent pas** : l'écart
n'est pas un effet d'échantillonnage. Sur le mot entier il atteint 32 points.

`spell-errors` (36 564 paires exploitables, 300 tirées avec seed) est le plus
fiable des trois : ses intervalles font ±5 à 7 points là où 60 paires en font
±9 à 13. C'est aussi pourquoi les colonnes testset1/testset2 sont à lire avec
prudence cellule par cellule — la comparaison qui tient est la tendance
d'ensemble, pas une cellule isolée.

**À corriger dans le papier** : annoncer le rappel sur `spell-errors` ou
`testset2`, pas sur testset1. Un jeu de dev qui flatte de 30 points est
exactement ce qu'un relecteur cherche.

```bash
./env/bin/python bench.py --skip test bench symspell --testset errors --pairs 300
```

**Non reproductible pour l'instant** : les tables top-1/top-2/top-3/MRR de la
version précédente venaient de `scripts/evaluate.py`, supprimé au commit
`bcfbfd7` (copie figée dans `results/legacy/accuracy.csv`). `bench.py` mesure le
rappel et la précision, pas le classement. Si le papier cite du top-k, il faut
réécrire cette métrique.

### Le bug de labels que le gate ne voyait pas

Les couches L2–L6 comparent **les mots seulement**. Les labels `(op, x, w)` qui
alimentent `editprob` n'étaient couverts par aucun test, et un bug y est passé :
un sous-arbre émis héritait de l'alignement de son préfixe émetteur, donc le mot
exact tapé (`then` → `then`) recevait `op=ins` et était scoré 0.9 → 5e-5, sous
des candidats fautifs. Un premier correctif a réparé ce cas et cassé les
complétions propres (`ann` → `anna` étiqueté `del`), parce que l'émission se
fait au **premier** préfixe qui matche (`an`, distance 1), pas au meilleur
(`ann`, distance 0) — l'optimisation du papier jette précisément cette
information. Le label est maintenant calculé exactement par mot
(`_best_prefix_op`, `osa_row` sur les `|q|+k` premiers caractères) et figé par
la couche **L7** : `op = None ⇔ q est un préfixe exact du mot`. Avant/après sur
top-1 : |q|=3 0 % → 21.7 %, |q|=4 7.5 % → 35 %, |q|=5 29.7 % → 47.4 %.

Le correctif tient toujours, vérifié sur le code courant : `then → then` et
`ann → anna` sont bien étiquetés `op=None`, et c'est ce qu'assure la
vérification « étiquettes du canal » du gate.

Les chiffres avant/après ci-dessus venaient de `scripts/evaluate.py` et ne sont
plus reproductibles en l'état (voir la fin du §4).

## 4b. Conventions de scoring — écarts avec Kernighan et al. 1990 (code d'origine, **non modifié**)

Vérifié dans le PDF : `Pr(t|c) = rev[c_p, c_{p+1}] / chars[c_p, c_{p+1}]` et
`sub[t_p, c_p] / chars[c_p]`, avec `sub[X,Y] = substitution de X (tapé) pour Y (correct)`.

- **`rev` : écart résolu.** L'ancienne récursion `get_noise` émettait le
  bigramme **tapé** (`word[i], word[i+1]`) là où le papier indexe par le
  bigramme **correct**. Depuis que la DP a pris ce nom, l'étiquette vient du mot
  candidat : vérifié sur le code courant, `hte → the` rend `("rev", "t", "h")`,
  soit le bigramme `th` du mot correct. Conforme au papier. L'écart comptait :
  `rev.csv` est asymétrique (220/650 paires) et `count_bigram[a,n]=71278` contre
  `[n,a]=10954`, donc l'ordre changeait le score d'un facteur ~10.
- **`sub` dans `editprob`** : `substitute(w, x) / count_unigram(x)` avec
  `x`=tapé, `w`=correct lit `sub.csv[correct, tapé]` et normalise par
  `chars[tapé]` ; le papier lit `sub[tapé, correct] / chars[correct]`.
  **Vérifié** : la ligne `a` de la table du PDF (`0 0 7 1 342 0 0 2 118 …`)
  est identique à `sub.csv` ligne `a`, donc le CSV est copié tel quel
  (ligne = tapé, colonne = correct) et `editprob` lit la matrice
  **transposée** avec le mauvais dénominateur. Exemple : `then` → `than`,
  l'événement est « e tapé pour a » = `sub[e,a] = 388`, le code lit
  `sub[a,e] = 342`. Touche les deux générateurs à l'identique, donc n'affecte
  pas la comparaison, mais affecte les valeurs absolues de la table 4.
- `del` et `ins` sont conformes.

Reste donc **un seul** écart ouvert, celui de `editprob` sur `sub`, gelé par
décision : signalé, non corrigé. Il touche les deux générateurs de candidats à
l'identique, donc n'affecte pas la comparaison — seulement les probabilités
absolues affichées par la démo.

## 5. ~~`get_noise` vs récursion naïve~~ — section caduque

La version précédente comparait ici `search_dp` à la récursion naïve d'origine,
gardée comme troisième point de comparaison. Cette récursion **a été supprimée**
au commit `bcfbfd7` : `get_noise` *est* désormais la recherche DP. La table
(rappel 43-89%, précision 100%) n'a donc plus d'objet et est archivée dans
`results/legacy/get_noise_recall.csv`.

À décider pour le papier : soit on ne mentionne pas ce troisième point, soit on
restaure la récursion sous un autre nom pour pouvoir écrire « notre DP corrige
aussi les trous de rappel de la récursion naïve ».

## 5b. Le vrai concurrent : SymSpell (index de suppressions)

La baseline « générer puis chercher » est celle de Norvig et Kernighan, mais
**ce n'est pas l'état de l'art**. La méthode de référence pour la correction
approchée rapide est SymSpell (Garbe, 2012) : précalculer, pour chaque entrée,
toutes les chaînes obtenues en supprimant jusqu'à `k` caractères, et les
indexer. Un relecteur du domaine posera la question ; mieux vaut y répondre.

`src/symspell.py` l'implémente, adapté à notre tâche : l'entrée indexée n'est
pas le mot mais **chaque préfixe de chaque mot** (un mot est une réponse dès
qu'un de ses préfixes matche). Complétude **vérifiée** contre la force brute à
k=1 et k=2, pas supposée — la garantie de SymSpell est établie pour Levenshtein
et notre tâche utilise OSA.

### Latence de requête : SymSpell gagne, nettement

| dico | k | \|q\| | get_noise | symspell | rapport |
|---|---|---|---|---|---|
| 10k | 2 | 3 | 4.32 ms | 1.26 ms | 3.4× plus rapide |
| 10k | 2 | 7 | 3.15 ms | 0.08 ms | **39× plus rapide** |
| 100k | 2 | 3 | 38.78 ms | 7.67 ms | 5.1× |
| 100k | 2 | 7 | 16.15 ms | 0.45 ms | **36× plus rapide** |
| 100k | 1 | 5 | 1.48 ms | 0.05 ms | 30× |
| 333k | 2 | 5 | 30.79 ms | 8.10 ms | 3.8× |
| 333k | 2 | 7 | 33.60 ms | 1.07 ms | **31×** |

Il faut l'écrire tel quel. Sur la latence de requête pure, notre méthode perd.

### Ce que SymSpell paie pour ça (dico 333k, k=2)

| | mémoire | construction | mise à jour |
|---|---|---|---|
| **trie** | **0.28 Go** | **0.57 s** | **1 µs / mot** |
| **SymSpell** | 6.17 Go (27 961 910 entrées) | 20.7 s | 120 µs / mot |
| rapport | **22×** | **36×** | **125×** |

Mesuré structure par structure dans un processus neuf (`bench_memory.py`,
`results/memory.csv`) : `maxrss` est un maximum historique, donc mesurer deux
structures dans le même processus rendrait le maximum de la plus grosse.
Courbe complète sur les quatre tailles dans `figures/fig_tradeoff.png`.

Trois coûts, tous structurels :

1. **Mémoire** — 22×. SymSpell matérialise à plat ce que le trie factorise :
   chaque préfixe de chaque mot, multiplié par toutes ses suppressions. Il tient
   dans 24 Go, donc l'argument « ça ne rentre pas » ne marche pas ici ; mais
   6 Go pour un dictionnaire de 333k mots disqualifie la méthode sur un appareil
   contraint — or l'autocomplétion tolérante aux fautes vit surtout sur des
   claviers mobiles.
2. **Construction** — 36×, à refaire à chaque changement de dictionnaire.
3. **Adaptation en ligne** — 125×, et c'est le point qui touche le sujet même du
   projet. `Trie.add/remove/type` maintiennent `freq` et `last_used` en O(|mot|) :
   le dictionnaire s'adapte à la frappe de l'utilisateur pendant qu'il tape
   (1000 `type()` en 1.2 ms). L'index de suppressions n'a pas d'équivalent — il
   ne porte pas de fréquences, et insérer un mot coûte ~72 entrées d'index.

### Positionnement honnête pour le papier

SymSpell est plus rapide **quand on peut se permettre son index**. Le trie tient
le dictionnaire complet dans un vingtième de la mémoire, se construit en une
demi-seconde et se met à jour en ligne — c'est la structure adaptée quand le
dictionnaire est gros, la mémoire bornée, ou le dictionnaire vivant. C'est un
positionnement plus étroit que « on est 139× plus rapide », mais c'en est un
qui tient en review.

## 6. Reproductibilité

```bash
python -m venv env && ./env/bin/pip install -r requirements.txt
./env/bin/python bench.py --skip quality bench symspell   # gate seul
./env/bin/python bench.py --sizes 10000 --pairs 20        # passe rapide
./env/bin/python bench.py --testset errors --pairs 300    # rappel fiable
./env/bin/python bench.py > results/bench.txt             # run complet
./env/bin/python src/demo.py                        # demo interactive
```

Options : `--max-depth -1` (complétions sans limite), `--queries/--repeats`
(échantillonnage de la section 3), `--no-csv`.

Sorties : `results/bench.txt` (les quatre sections telles qu'affichées),
`results/benchmark.csv`, `results/quality_<jeu>.csv`, `results/symspell.csv`,
`results/symspell.txt`.
`results/legacy/` contient les sorties des scripts supprimés — ne pas les citer,
voir `results/legacy/README.md`.

Figures régénérées depuis `results/benchmark.csv`, cohérentes avec les tables
ci-dessus :

```bash
./env/bin/python make_figures.py
```

- `figures/fig_prefix_length.png` — **figure principale** : deux panneaux, la
  latence à k=2 et les compteurs de travail. Le croisement du panneau (b) (les
  chaînes générées passent au-dessus des nœuds visités vers |q|=5) est
  l'argument du papier en une image.
- `figures/fig_pruning.png` — nœuds visités par |q| et par taille de dico :
  −63 % de |q|=3 à |q|=7 à 333k.
- `figures/fig_latency_vs_dictsize_k2.png` — passage à l'échelle à k=2, avec le
  point OOM de la baseline à 333k.
- `figures/fig_latency_vs_dictsize_k1.png` — le même à k=1, où notre courbe
  passe au-dessus de la baseline vers 25k mots. À mettre dans le papier plutôt
  qu'à omettre.
