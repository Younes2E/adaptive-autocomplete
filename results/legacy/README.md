# Resultats orphelins (ne pas citer dans le papier)

Ces fichiers ont ete produits par `scripts/benchmark.py`, `scripts/evaluate.py`
et `scripts/get_noise_recall.py`, supprimes au commit `bcfbfd7` quand tout a ete
regroupe dans `bench.py`. Ils decrivent l'ancienne API (`search_dp` d'un cote,
`get_noise` recursion naive de l'autre), qui n'existe plus : `get_noise` *est*
maintenant la recherche DP.

En particulier `get_noise_recall.csv` compare `search_dp` a une recursion naive
qui a ete supprimee -- le tableau n'a plus d'objet.

De plus, ce run a tourne en concurrence d'autres calculs : ses latences absolues
sont ~4x trop hautes.

Table courante : `results/bench.txt`, `results/benchmark.csv`,
`results/quality.csv` (produits par `python bench.py`).
