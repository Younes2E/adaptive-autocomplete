# Résultats mesurés — autocomplétion tolérante aux fautes sur Trie

Tout ce qui suit est reproductible par `python run_all.py`. Machine : AMD64,
Windows 11, Python 3.12.6, numpy 2.4.3 / pandas 3.0.2. Seed 42.

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

## 2. Correction (T4) — le gate passe

13 tests, dont :
- **anti-circularité** : le lemme « dernière ligne DP = distances à tous les
  préfixes » validé sur 3000 paires aléatoires contre une énumération naïve.
  Sans ça, référence et `search_dp` pourraient être faux à l'identique.
- **régressions nommées** : `hte→the`, `acr→car`, `cra→{access,act}`.
- **égalité exacte d'ensembles** vs force brute à 20k et 50k (exhaustif),
  100k et 333k (échantillonné).
- `search_dp == baseline` ; `get_noise` gelée (signature + sortie).

Bug trouvé et corrigé par le gate : la règle de transposition OSA utilisait la
ligne du parent (`row[i-2]`) au lieu du grand-parent (`prow[i-2]`), et était
gardée sur `pchar` — désactivée à la profondeur 2, elle ratait silencieusement
toutes les transpositions en début de mot.

## 3. Performance (T3) — grille complète, 1056 mesures, run final (code post-correctif labels)

**Note de méthode** : ce run a tourné en parallèle d'autres calculs sur la même
machine (vérifications de sources, comparaisons PDF) ; les latences absolues de
`search_dp` sont donc ~2× plus hautes que dans une mesure isolée (ex. 10k/|q|=5 :
6.8 ms → 14.6 ms). C'est du bruit de contention, pas un changement de
comportement — `search_dp` est chronométré avec `with_ops=False`, donc le
correctif sur les labels de canal ne touche pas ce chemin. **Le facteur de gain
(search_dp vs baseline) est stable d'un run à l'autre** et c'est lui qui porte
l'argument du papier ; pour une table finale, relancer `scripts/benchmark.py`
sur une machine au repos.

### Table 1 : effet de la longueur de préfixe (k=2) — l'argument central

| dico | \|q\| | search_dp | nœuds | élagués | baseline | gain |
|---|---|---|---|---|---|---|
| 10k | 3 | 12.2 ms | 8202 | 1443 | 194 ms | 16× |
| 10k | 5 | 14.6 ms | 4050 | 2445 | 893 ms | 61× |
| 10k | 7 | 18.5 ms | 3811 | 2482 | 3042 ms | 164× |
| 50k | 3 | 47.8 ms | 42198 | 4876 | 183 ms | 4× |
| 50k | 5 | 49.2 ms | 12857 | 8476 | 925 ms | 19× |
| 50k | 7 | 54.1 ms | 10981 | 8075 | 2941 ms | 54× |
| 100k | 5 | 78.9 ms | 17838 | 12727 | 1038 ms | 13× |
| 100k | 7 | 107.9 ms | 19772 | 14868 | 3260 ms | 30× |
| 333k | 5 | 160.9 ms | 42405 | 29766 | OOM | — |
| 333k | 7 | 191.7 ms | 37088 | 29660 | OOM | — |

Même tendance que le run précédent : le gain croît avec la longueur du préfixe
à dictionnaire fixe (16×→164× à 10k), parce que la baseline énumère toutes les
variantes puis toutes leurs complétions (194 ms → 3042 ms), tandis que
`search_dp` reste quasi plat.

### Table 2 : scaling en taille de dictionnaire (\|q\|=5, k=2)

| dico | search_dp | nœuds | baseline | gain |
|---|---|---|---|---|
| 10k | 14.6 ms | 4 050 | 893 ms | 61× |
| 50k | 49.2 ms | 12 857 | 925 ms | 19× |
| 100k | 78.9 ms | 17 838 | 1038 ms | 13× |
| 333k | 160.9 ms | 42 405 | **OOM** | — |

Même lecture que précédemment : le gain décroît avec la taille du dictionnaire
(la baseline est insensible à la taille, `search_dp` grandit avec la densité du
trie) — deux moteurs de coût orthogonaux, un résultat plutôt qu'une faiblesse.
À k=1 la baseline reste compétitive. OOM à 333k : l'index préfixe est plafonné
à 100k mots, résultat publiable en soi.

## 4. Qualité (T5) — testset1, dico 20k, 60 paires, ventilé par longueur de préfixe

| k | \|q\| | candidats | recall | top-1 | top-2 | top-3 | MRR |
|---|---|---|---|---|---|---|---|
| 1 | 2 | 3880 | 100.0% | 3.3% | 3.3% | 5.0% | 0.039 |
| 1 | 3 | 482 | 100.0% | 21.7% | 26.7% | 36.7% | 0.275 |
| 1 | 4 | 75 | 96.7% | 35.0% | 46.7% | 56.7% | 0.442 |
| 1 | 5 | 12 | 96.5% | 47.4% | 66.7% | 71.9% | 0.588 |
| 1 | 6 | 4 | 88.7% | 60.4% | 69.8% | 73.6% | 0.664 |
| 1 | 7 | 1 | 70.5% | 52.3% | 61.4% | 65.9% | 0.583 |
| 2 | 3 | 6806 | 100.0% | 21.7% | 23.3% | 33.3% | 0.258 |
| 2 | 4 | 1164 | 100.0% | 23.3% | 31.7% | 46.7% | 0.325 |
| 2 | 5 | 237 | 100.0% | 31.6% | 50.9% | 52.6% | 0.418 |
| 2 | 6 | 40 | 100.0% | 41.5% | 50.9% | 52.8% | 0.469 |
| 2 | 7 | 10 | 100.0% | 52.3% | 65.9% | 70.5% | 0.606 |

**Le recall est ~100 % dès 2 caractères** : la recherche trouve toujours le bon
mot ; c'est la métrique côté *recherche*. Le top-1 est la métrique côté
*scoring* et dépend du nombre de candidats à départager (3880 → 1). Agréger sur
les longueurs produirait un chiffre vide de sens — d'où la ventilation. À k=2 le
recall reste à 100 % jusqu'à |q|=7 là où k=1 tombe à 70 % : le rayon 2 rattrape
les fautes que le préfixe de 7 lettres du mot fautif contient.

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

Le benchmark mesure `search_dp` avec `with_ops=False` : recherche contre
recherche, la baseline ne produisant aucun label.

## 4b. Conventions de scoring — écarts avec Kernighan et al. 1990 (code d'origine, **non modifié**)

Vérifié dans le PDF : `Pr(t|c) = rev[c_p, c_{p+1}] / chars[c_p, c_{p+1}]` et
`sub[t_p, c_p] / chars[c_p]`, avec `sub[X,Y] = substitution de X (tapé) pour Y (correct)`.

- **`rev` dans `get_noise`** émet le bigramme **tapé** (`word[i], word[i+1]`) ;
  le papier indexe par le bigramme **correct**. `search_dp` suit le papier.
  `rev.csv` est asymétrique (220/650 paires) et `count_bigram[a,n]=71278` vs
  `[n,a]=10954` : l'ordre change le score d'un facteur ~10. Figé en test L7.
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

Ces deux points sont dans ton code, gelé par décision : je les signale, je ne
les corrige pas.

## 5. `get_noise` — précision parfaite, recall très partiel (dico 20k)

| k | \|q\| | réf | recall | précision | extras |
|---|---|---|---|---|---|
| 1 | 2 | 3466 | **43.4%** | 100% | 0 |
| 1 | 4 | 110 | 59.2% | 100% | 0 |
| 1 | 6 | 4 | 93.8% | 100% | 0 |
| 2 | 3 | 6522 | **54.4%** | 100% | 0 |
| 2 | 5 | 314 | 65.7% | 100% | 0 |
| 2 | 7 | 25 | 88.8% | 100% | 0 |

`search_dp` est à 100 % de recall sur toutes ces cellules.
Nuance par rapport à la description initiale : les trous de recall ne sont pas
« étroits » — sur préfixes courts `get_noise` rate **plus de la moitié** des
réponses. En revanche il ne produit aucun faux positif (précision 100 %), ce qui
est cohérent avec une récursion qui explore trop peu de chemins d'alignement.

## 6. Reproductibilité

```bash
python run_all.py --quick     # gate + grille réduite
python run_all.py --full      # grille complète + gate 333k
python tests/test_correctness.py   # doit sortir 0
```

Sorties : `results/benchmark_{raw,agg}.csv`, `results/accuracy.csv`,
`results/get_noise_recall.csv`, `results/manifest.json`, `figures/*.png`.
