from utils import osa_row

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False
        self.freq = 0
        self.last_used = 0

    def is_empty(self):
        return not self.is_word and len(self.children) == 0


class Trie:
    def __init__(self):
        self.root = TrieNode()
        self.nb_typed = 0
        self.visited_nodes = 0

    def add(self, word, freq=0):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_word = True
        node.freq = freq
        self.nb_typed += freq

    def remove(self, word):
        def loop(node, depth):
            if depth == len(word):
                if not node.is_word:
                    raise KeyError(f'{word} not found')
                else:
                    node.is_word = False
                    self.nb_typed -= node.freq
                    node.freq = 0
                    node.last_used = 0
            elif word[depth] not in node.children:
                raise KeyError(f'{word} not found')
            else:
                char = word[depth]
                child = node.children[char]
                loop(child, depth + 1)
                if child.is_empty():
                    del node.children[char]
        loop(self.root, 0)

    def type(self, word):
        def loop(node, depth):
            if depth == len(word):
                node.freq += 1
                self.nb_typed += 1
                node.last_used = self.nb_typed
            elif word[depth] not in node.children:
                raise KeyError(f'{word} not found')
            else:
                char = word[depth]
                loop(node.children[char], depth + 1)
        loop(self.root, 0)

    def get_noise(self, word, distance=1, max_depth=3):
        """Candidats d'autocompletion tolerante aux fautes, en UN parcours du Trie.

        Retourne les mots w tels que:
          - un prefixe p de w verifie OSA(word, p) <= distance
          - len(w) <= len(word) + max_depth   (max_depth=None : sans limite)

        Chaque noeud porte une ligne de DP calculee depuis celle de son parent.
        Pour un noeud de chemin p, ligne[i] = OSA(word[:i], p), donc ligne[n]
        est la distance entre la requete complete et p.

        Deux regles:
          EMISSION : ligne[n] <= distance -> p matche, donc TOUS les mots du
            sous-arbre sont des reponses (p est leur prefixe). On les enumere
            sans refaire de DP.
          ELAGAGE : min(ligne) > distance -> aucun descendant ne pourra matcher
            (le minimum ne redescend jamais quand on descend), on coupe.

        Format de sortie inchange : [mot, op, x, w, freq, last_used].
        self.visited_nodes compte les noeuds examines (metrique du benchmark).
        """
        n = len(word)
        self.visited_nodes = 0
        results = []
        max_len = None if max_depth is None else n + max_depth

        def emit_subtree(node, prefix):
            """Tout le sous-arbre matche : simple DFS, plus aucun calcul de DP."""
            stack = [(node, prefix)]
            while stack:
                nd, p = stack.pop()
                self.visited_nodes += 1
                if nd.is_word:
                    op, x, w = self._label(word, p, distance)
                    results.append([p, op, x, w, nd.freq, nd.last_used])
                if max_len is not None and len(p) >= max_len:
                    continue
                for ch, child in nd.children.items():
                    stack.append((child, p + ch))

        # ligne de la racine : OSA(word[:i], "") = i
        root_row = list(range(n + 1))
        # pile : (noeud, chemin, sa ligne, la ligne du PARENT, son caractere)
        stack = [(self.root, "", root_row, None, None)]
        while stack:
            node, path, row, prow, char = stack.pop()
            for ch, child in node.children.items():
                if max_len is not None and len(path) + 1 > max_len:
                    continue                        # trop long, inutile de calculer
                self.visited_nodes += 1
                cur = [row[0] + 1]
                for i in range(1, n + 1):
                    cost = 0 if word[i - 1] == ch else 1
                    v = min(row[i] + 1,          # suppression
                            cur[i - 1] + 1,      # insertion
                            row[i - 1] + cost)   # match ou substitution
                    # Transposition OSA : elle a besoin de DEUX caracteres de
                    # contexte, donc de la ligne du GRAND-PARENT (prow) et du
                    # caractere du parent (char). Utiliser row a la place
                    # desactive la regle a la profondeur 2 : hte->the et
                    # acr->car sont alors rates en silence.
                    if (i > 1 and prow is not None
                            and word[i - 1] == char and word[i - 2] == ch):
                        v = min(v, prow[i - 2] + 1)
                    cur.append(v)

                if cur[n] <= distance:
                    emit_subtree(child, path + ch)
                elif min(cur) > distance:
                    pass                                    # elagage
                else:
                    stack.append((child, path + ch, cur, row, ch))

        return results

    @staticmethod
    def _label(word, candidate, distance):
        """Operation du canal bruite entre la requete et le mot retenu.

        L'emission se fait au premier prefixe qui matche, pas au meilleur, donc
        l'etiquette est recalculee mot par mot : osa_row donne OSA(word, w[:j])
        pour tout j en une passe, on garde le meilleur j (le plus long en cas
        d'egalite). Sans ca, un mot tape correctement herite de l'alignement du
        prefixe emetteur et se retrouve score comme une faute.
        """
        row = osa_row(word, candidate[:len(word) + distance])
        best = min(row)
        j = max(i for i, d in enumerate(row) if d == best)
        prefix = candidate[:j]
        if word == prefix:
            return (None, None, None)
        n, m = len(word), len(prefix)
        i = 0
        while i < min(n, m) and word[i] == prefix[i]:
            i += 1
        if i >= n and i >= m:
            return (None, None, None)
        if n == m:
            if i + 1 < n and word[i] == prefix[i + 1] and word[i + 1] == prefix[i]:
                return ("rev", prefix[i], prefix[i + 1])
            return ("sub", word[i], prefix[i])
        if m == n + 1:
            # le prefixe a un caractere de plus : il a ete oublie a la frappe
            return ("del", prefix[i - 1] if i > 0 else '@', prefix[i])
        if m == n - 1:
            # la requete a un caractere de trop : il a ete ajoute a la frappe
            return ("ins", prefix[i - 1] if i > 0 else '@', word[i])
        # distance >= 2 : pas d'edition unique, on rend l'edition terminale
        return ("sub", word[i] if i < n else '@', prefix[i] if i < m else '@')

    def load_dict(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    word = parts[0].lower()
                    try:
                        frequency = int(parts[1])
                        self.add(word, freq=frequency)
                    except Exception:
                        continue
