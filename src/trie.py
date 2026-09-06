import json

from utils import osa_row

class TrieNode:
    # ~1M nodes at 333k words, so __slots__ is a real memory saving.
    __slots__ = ('children', 'is_word', 'freq', 'last_used')

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
        self.stats = {}

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
                if not node.is_word :
                    raise KeyError(f'{word} not found')
                else :
                    node.is_word = False
                    self.nb_typed -= node.freq
                    node.freq = 0
                    node.last_used = 0
            elif word[depth] not in node.children : 
                raise KeyError(f'{word} not found') 
            else :
                char = word[depth]
                child = node.children[char]
                loop(child, depth+1)
                if child.is_empty() :
                    del node.children[char]
        loop(self.root, 0)

    def type(self, word):
        def loop(node, depth):
            if depth == len(word):
                node.freq += 1
                self.nb_typed += 1
                node.last_used = self.nb_typed
            elif word[depth] not in node.children : 
                raise KeyError(f'{word} not found')
            else:
                char = word[depth]
                loop(node.children[char], depth+1)   
        loop(self.root, 0)

    def get_noise(self, word, distance = 1, max_depth=3):
        result = []
        n = len(word)
        def loop(node, i, distance, buffer, operation = None, x=None, w=None):
            if node.is_word and i >= n - distance: 
                op, curr_x, curr_w = operation, x, w
                if i < n :
                    op, curr_x, curr_w = "ins", buffer[-1] if i > 0 else '@', word[i]
                result.append([buffer, op, curr_x, curr_w, node.freq, node.last_used])
            if i <= n + max_depth :
                for char in node.children :
                    if i >= n or char == word[i]  :
                        loop(node.children[char], i+1, distance, buffer+char,operation, x, w)
                    elif distance > 0 :
                        loop(node.children[char], i+1, distance-1, buffer+char, "sub", word[i], char)
                        loop(node.children[char], i, distance-1, buffer+char,  "del", buffer[-1] if i > 0 else '@', char) 
                        if i < n - distance and char == word[i+1]:
                            loop(node.children[char], i+2, distance -1, buffer+char, "ins",buffer[-1] if i > 0 else '@', word[i])
                            if word[i] in node.children[char].children:
                                loop(node.children[char].children[word[i]], i+2, distance -1, buffer+char+word[i], "rev",word[i], word[i+1])
        loop(self.root, 0, distance, "")
        return result
    
    def search_dp(self, query, max_dist=2, max_completion=None, with_ops=True):
        """Error-tolerant autocompletion: one DP-carrying traversal of the Trie.

        Returns every word w such that SOME prefix p of w satisfies
        OSA(query, p) <= max_dist -- correction and completion resolved in a
        single pass.

        A DP row is carried down each branch. At a node with path-label p, the
        row holds OSA(query[:i], p) for i = 0..|query|, so row[|query|] is
        exactly OSA(query, p). Two rules do the work:

          emission -- row[|query|] <= max_dist means p itself matches, so EVERY
            word in that subtree is a valid completion. The subtree is
            enumerated directly with no further DP. This is what makes the
            structure necessary rather than merely faster.

          pruning -- min(row) > max_dist means no descendant can ever match
            (row values never decrease below the current minimum), so the whole
            subtree is cut.

        max_completion bounds how many characters a word may extend past the
        matched prefix. Per-query counters land in self.stats.

        with_ops=False skips the channel-operation labels (op, x, w are None):
        the retrieval set is identical, and that is the fair setting for the
        benchmark since the generate-and-lookup baseline yields no labels.

        Rows are [word, op, x, w, freq, last_used], the shape get_noise()
        returns, so the existing noisy-channel scoring consumes them unchanged.
        """
        n = len(query)
        visited = pruned = emitted = 0
        results = []

        def enumerate_subtree(node, prefix, budget):
            """Pure DFS over a matching subtree -- no DP, no distance checks.

            Labels are computed per word by _best_prefix_op, not inherited from
            the emitting prefix: emission happens at the SHALLOWEST matching
            node ("an" for query "ann"), so the emitting prefix's alignment is
            not the best explanation of every word below it ("anna" completes
            "ann" exactly and must keep op=None; "then" typed and found is
            exact, not an insertion on "the").
            """
            nonlocal visited
            stack = [(node, prefix, 0)]
            while stack:
                nd, pref, depth = stack.pop()
                visited += 1
                if nd.is_word:
                    op, x, w = (self._best_prefix_op(query, pref, max_dist)
                                if with_ops else (None, None, None))
                    results.append([pref, op, x, w, nd.freq, nd.last_used])
                if budget is not None and depth >= budget:
                    continue
                for ch, child in nd.children.items():
                    stack.append((child, pref + ch, depth + 1))

        root_row = list(range(n + 1))
        # With k < |query| enforced by the query generator, the empty prefix
        # never matches; guard anyway so a degenerate call is loud, not silent.
        if root_row[n] <= max_dist:
            raise ValueError(
                f"degenerate query: |query|={n} <= max_dist={max_dist}; the empty "
                f"prefix matches, so the answer is the whole dictionary")

        # stack entries: (node, path, its DP row, its parent's row, its char)
        stack = [(self.root, "", root_row, None, None)]
        while stack:
            node, path, row, prow, char = stack.pop()
            for ch, child in node.children.items():
                visited += 1
                cur = [row[0] + 1]
                for i in range(1, n + 1):
                    cost = 0 if query[i - 1] == ch else 1
                    v = min(row[i] + 1,          # deletion
                            cur[i - 1] + 1,      # insertion
                            row[i - 1] + cost)   # match / substitution
                    # OSA transposition, d[i-2][j-2]+1. For the child at
                    # path+ch the preceding character is `char` and d[.][j-2]
                    # lives in the grandparent row `prow`. Using `row` here, or
                    # gating on the parent character, disables the rule at depth
                    # 2 and silently drops hte->the and acr->car.
                    if (i > 1 and prow is not None
                            and query[i - 1] == char and query[i - 2] == ch):
                        v = min(v, prow[i - 2] + 1)
                    cur.append(v)

                if cur[n] <= max_dist:
                    emitted += 1
                    enumerate_subtree(child, path + ch, max_completion)
                elif min(cur) > max_dist:
                    pruned += 1
                else:
                    stack.append((child, path + ch, cur, row, ch))

        self.stats = {
            'visited_nodes': visited,
            'pruned_subtrees': pruned,
            'emitted_subtrees': emitted,
            'emitted_words': len(results),
            'dp_cells': visited * (n + 1),
        }
        return results

    @staticmethod
    def _best_prefix_op(query, word, max_dist):
        """Channel operation for the best-matching prefix of `word`.

        osa_row gives OSA(query, word[:j]) for every j in one pass. Only the
        first len(query)+max_dist characters can matter: a deeper prefix is at
        distance > max_dist by length alone, so it can never be the best match
        of a retrieved word. Ties go to the longest prefix, i.e. the reading
        "the user misspelled the whole word" is preferred over "the user typed
        a shorter word correctly and this is a completion".
        """
        n = len(query)
        row = osa_row(query, word[:n + max_dist])
        best = min(row)
        j = max(i for i, d in enumerate(row) if d == best)
        return Trie._alignment_op(query, word[:j])

    @staticmethod
    def _alignment_op(query, prefix):
        """Channel operation for the query -> matched-prefix alignment.

        editprob() scores a single edit, but an emitted subtree at k=2 shares a
        two-edit alignment. We report the terminal edit of the optimal
        alignment, which is exact for k=1 (matching get_noise semantics) and an
        approximation for k>1 -- stated explicitly in the paper. Returning None
        for multi-edit candidates would hand them the flat 0.9 and rank
        distance-2 candidates above distance-1 ones.

        '@' marks the word boundary, following Kernighan et al. 1990.
        """
        if query == prefix:
            return (None, None, None)
        n, m = len(query), len(prefix)
        i = 0
        while i < min(n, m) and query[i] == prefix[i]:
            i += 1
        if i >= n and i >= m:
            return (None, None, None)
        if n == m:
            if i + 1 < n and query[i] == prefix[i + 1] and query[i + 1] == prefix[i]:
                return ("rev", prefix[i], prefix[i + 1])
            return ("sub", query[i], prefix[i])
        if m == n + 1:
            # the prefix carries an extra character -> it was deleted when typing
            return ("del", prefix[i - 1] if i > 0 else '@', prefix[i])
        if m == n - 1:
            # the query carries an extra character -> it was inserted when typing
            return ("ins", prefix[i - 1] if i > 0 else '@', query[i])
        return ("sub", query[i] if i < n else '@', prefix[i] if i < m else '@')

    def iter_words(self):
        """Yield (word, freq, last_used) for every word in the trie."""
        stack = [(self.root, "")]
        while stack:
            node, prefix = stack.pop()
            if node.is_word:
                yield prefix, node.freq, node.last_used
            for ch, child in node.children.items():
                stack.append((child, prefix + ch))

    def load_dict(self, file_path, limit=None):
        """Load 'word<TAB>freq' lines. The file is already sorted by descending
        frequency, so `limit` subsamples the top-N most frequent words."""
        loaded = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    word = parts[0].lower()
                    try:
                        frequency = int(parts[1])
                        self.add(word, freq = frequency)
                        loaded += 1
                    except Exception:
                        continue
                    if limit is not None and loaded >= limit:
                        break
        return loaded

def main():
    trie = Trie()
    trie.add("irrespect")
    trie.add("arbre")
    trie.add("arret")
    trie.add("barre")
    trie.add("air")
    trie.add("arrets")
    trie.add("apres")
    trie.add("arrivererasqhsdsjsd")
    
    trie.add("actress")
    trie.add("cress")
    trie.add("caress")
    trie.add("access")
    trie.add("across")
    trie.add("acres")
    trie.add("acre")

    trie.add("then")
    trie.add("than")
    trie.add("them")
    trie.add("the")



    print("Autocomplete de \"then\"\n",trie.get_noise("then"),"\n")


if __name__ == "__main__":
    main()