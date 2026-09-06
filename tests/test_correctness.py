"""T4 -- mandatory correctness gate. Nothing downstream is meaningful until this
passes: benchmarking an incorrect function measures nothing.

Layers, cheapest first:
  L0  anti-circularity + named distance facts
  L1  named transposition regressions
  L2  exhaustive set equality at 20k
  L3  exhaustive set equality at 50k
  L4  sampled equality at 100k / 333k   (--full only)
  L5  search_dp == baseline
  L6  get_noise unchanged (golden snapshot)
"""
import os
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from trie import Trie                                    # noqa: E402
from utils import osa, min_prefix_distance               # noqa: E402
from reference import (reference_search, reference_search_naive,  # noqa: E402
                       min_prefix_distance_naive)
from dataset import load_trie, load_vocab                # noqa: E402
from queries import cells, make_queries                  # noqa: E402

FULL = os.environ.get("GATE_FULL") == "1"

TOY = ['the', 'then', 'access', 'act', 'car', 'cars', 'crazy', 'for', 'from',
       'he', 'at', 'hat', 'ate', 'tea', 'acre', 'acres', 'across', 'apple']


def toy_trie():
    t = Trie()
    for w in TOY:
        t.add(w, freq=1)
    return t


class L0_AntiCircularity(unittest.TestCase):
    """The reference and search_dp share the 'last DP row = prefix distances'
    lemma. If that lemma were wrong both would be wrong identically and every
    other layer would pass vacuously. Check it against naive enumeration."""

    def test_lemma_vs_naive_enumeration(self):
        rng = random.Random(1)
        alpha = "abc"
        for _ in range(3000):
            a = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 6)))
            b = "".join(rng.choice(alpha) for _ in range(rng.randint(0, 6)))
            self.assertEqual(min_prefix_distance(a, b),
                             min_prefix_distance_naive(a, b),
                             f"lemma broken for {a!r}/{b!r}")

    def test_reference_impls_agree(self):
        for q in ["cra", "hte", "acr", "the", "appl"]:
            for k in (1, 2):
                if k >= len(q):
                    continue
                self.assertEqual(reference_search(q, TOY, k),
                                 reference_search_naive(q, TOY, k), f"{q}/{k}")

    def test_named_distance_facts(self):
        # CLAUDE.md's example has the right conclusion but the wrong witness:
        # "cra" reaches "access"/"act" through prefix "a", not "ac".
        self.assertEqual(osa("cra", "a"), 2)
        self.assertEqual(osa("cra", "ac"), 3)
        self.assertEqual(min_prefix_distance("cra", "access"), 2)
        # OSA is restricted Damerau: a transposed substring cannot be re-edited.
        self.assertEqual(osa("rf", "for"), 3)

    def test_confusion_matrix_orientation(self):
        # sub.csv is Kernighan et al. 1990's table verbatim: row X = typed
        # (incorrect), column Y = correct. Row 'a' of the paper reads
        # 0 0 7 1 342 0 0 2 118 ... -- so sub[a, e] = 342 is "a typed for e".
        # noisy_channel.editprob currently reads substitute(correct, typed);
        # this pins the data so that whoever fixes it has a fixed reference.
        import pandas as pd
        sub = pd.read_csv(ROOT / "data" / "matrices" / "sub.csv", index_col=0)
        self.assertEqual(int(sub.at["a", "e"]), 342)
        self.assertEqual(int(sub.at["e", "a"]), 388)
        self.assertEqual([int(v) for v in sub.loc["a"][:9]], [0, 0, 7, 1, 342, 0, 0, 2, 118])


class L1_TranspositionRegressions(unittest.TestCase):
    """These pass under a naive k=1 smoke test even when the transposition rule
    is disabled at depth 1, which is why they are pinned by name."""

    def setUp(self):
        self.t = toy_trie()

    def _words(self, q, k):
        return {r[0] for r in self.t.search_dp(q, max_dist=k)}

    def test_hte_finds_the(self):
        got = self._words("hte", 1)
        self.assertIn("the", got)
        self.assertIn("then", got)

    def test_acr_finds_car(self):
        got = self._words("acr", 1)
        self.assertIn("car", got)
        self.assertIn("cars", got)

    def test_cra_finds_access_and_act(self):
        got = self._words("cra", 2)
        self.assertIn("access", got)
        self.assertIn("act", got)

    def test_toy_exhaustive(self):
        for q in ["cra", "hte", "acr", "act", "the", "appl", "aple", "xyz"]:
            for k in (1, 2):
                if k >= len(q):
                    continue
                self.assertEqual(self._words(q, k), reference_search(q, TOY, k),
                                 f"{q}/{k}")


class L2_Exhaustive20k(unittest.TestCase):
    SIZE = 20_000
    NQ = 3

    def test_matches_reference(self):
        trie = load_trie(self.SIZE)
        vocab = load_vocab(self.SIZE)
        for L, k in cells():
            for q in make_queries(vocab, L, self.NQ):
                got = {r[0] for r in trie.search_dp(q, max_dist=k)}
                self.assertEqual(got, reference_search(q, vocab, k),
                                 f"query={q!r} k={k} size={self.SIZE}")


class L3_Exhaustive50k(L2_Exhaustive20k):
    SIZE = 50_000
    NQ = 2


@unittest.skipUnless(FULL, "set GATE_FULL=1 for the large sampled layer")
class L4_Sampled(unittest.TestCase):
    def test_large_dictionaries(self):
        for size in (100_000, 333_333):
            trie = load_trie(size)
            vocab = load_vocab(size)
            for L, k in [(4, 2), (6, 2)]:
                for q in make_queries(vocab, L, 2):
                    got = {r[0] for r in trie.search_dp(q, max_dist=k)}
                    self.assertEqual(got, reference_search(q, vocab, k),
                                     f"query={q!r} k={k} size={size}")


class L5_VersusBaseline(unittest.TestCase):
    SIZE = 20_000

    def test_search_dp_equals_baseline(self):
        from baseline import baseline_search, build_prefix_index
        trie = load_trie(self.SIZE)
        vocab = load_vocab(self.SIZE)
        index = build_prefix_index(vocab)
        for L, k in [(3, 1), (4, 2), (5, 2)]:
            for q in make_queries(vocab, L, 2):
                dp = {r[0] for r in trie.search_dp(q, max_dist=k)}
                bl = baseline_search(q, index, max_dist=k)
                self.assertEqual(dp, bl, f"query={q!r} k={k}")


class L6_GetNoiseFrozen(unittest.TestCase):
    """get_noise is the third comparison point and must not drift."""

    def test_output_shape_and_stability(self):
        t = toy_trie()
        rows = t.get_noise("then")
        self.assertTrue(all(len(r) == 6 for r in rows))
        got = sorted(r[0] for r in rows)
        # Pin the exact candidate set produced by the frozen implementation.
        self.assertEqual(got, ['the', 'then'])

    def test_signature_unchanged(self):
        import inspect
        sig = list(inspect.signature(Trie.get_noise).parameters)
        self.assertEqual(sig, ['self', 'word', 'distance', 'max_depth'])



class L7_ChannelLabels(unittest.TestCase):
    """L2-L6 compare words only and ignore op/x/w entirely. Those labels feed
    the noisy-channel score, and a wrong one was found by eye, not by a test:
    the exact typed word inherited an 'ins' from its emitting prefix and was
    scored as a typo (0.9 -> 5e-5). This layer pins the label semantics.

    Under the prefix task, a label is derived from the task definition, not
    from what the code happens to do: op is None iff the query is itself a
    prefix of the word (min prefix distance 0) -- a clean completion carries
    no edit. Anything else carries exactly one edit label.
    """

    def test_named_cases(self):
        t = Trie()
        for w in ["the", "then", "them", "than", "ann", "anna", "nan"]:
            t.add(w, freq=1)
        ops = {r[0]: r[1] for r in t.search_dp("then", max_dist=1)}
        self.assertIsNone(ops["then"])          # exact word, not 'ins' on "the"
        self.assertEqual(ops["them"], "sub")
        ops = {r[0]: tuple(r[1:4]) for r in t.search_dp("ann", max_dist=1)}
        self.assertEqual(ops["anna"], (None, None, None))   # clean completion
        # rev is indexed by the CORRECT bigram: Kernighan et al. 1990 define
        # rev[x,y] as the number of times "xy" was reversed, normalised by
        # chars[x,y], the count of "xy" in the (correct) training text.
        self.assertEqual(ops["nan"], ("rev", "n", "a"))

    def test_label_iff_prefix_distance_20k(self):
        trie, vocab = load_trie(20_000), load_vocab(20_000)
        for L, k in cells():
            if L < 3:
                continue
            for q in make_queries(vocab, L, 5):
                for r in trie.search_dp(q, max_dist=k):
                    d = min_prefix_distance(q, r[0])
                    self.assertEqual(r[1] is None, d == 0,
                                     f"{q!r}->{r[0]!r} op={r[1]} min_prefix={d}")

    def test_with_ops_false_same_set(self):
        trie, vocab = load_trie(20_000), load_vocab(20_000)
        for q in make_queries(vocab, 4, 4):
            a = trie.search_dp(q, max_dist=2)
            b = trie.search_dp(q, max_dist=2, with_ops=False)
            self.assertEqual({r[0] for r in a}, {r[0] for r in b})
            self.assertTrue(all(r[1] is None for r in b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
