from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trie import Trie


def build_trie(words):
    trie = Trie()
    for word in words:
        trie.add(word)
    return trie


class TrieTests(unittest.TestCase):
    def test_add_and_search_words(self):
        trie = build_trie(["car", "cart", "dog"])

        self.assertTrue(trie.search("car"))
        self.assertTrue(trie.search("cart"))
        self.assertTrue(trie.search("dog"))
        self.assertFalse(trie.search("ca"))
        self.assertFalse(trie.search("cat"))

    def test_remove_word_keeps_shared_prefix_branch(self):
        trie = build_trie(["car", "cart"])

        trie.remove("car")

        self.assertFalse(trie.search("car"))
        self.assertTrue(trie.search("cart"))
        self.assertIn("r", trie.root.children["c"].children["a"].children)

    def test_remove_prunes_unused_branch(self):
        trie = build_trie(["dog"])

        trie.remove("dog")

        self.assertFalse(trie.search("dog"))
        self.assertEqual(trie.root.children, {})

    def test_type_updates_frequency_and_last_used_ordering(self):
        trie = build_trie(["car", "cart", "cat"])

        trie.type("cat")
        trie.type("car")
        trie.type("car")

        self.assertEqual(trie.nb_typed, 3)
        self.assertEqual(trie.get("ca", n=3), ["car", "cat", "cart"])

    def test_get_respects_max_depth_from_prefix(self):
        trie = build_trie(["car", "cart", "carbon"])

        self.assertEqual(trie.get("ca", n=5, max_depth=1), ["car"])

    def test_save_and_load_round_trip(self):
        trie = build_trie(["car", "cart", "dog"])
        trie.type("car")
        trie.type("dog")
        trie.type("dog")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "trie.json"
            trie.save(str(save_path))

            loaded = Trie().load(str(save_path))

        self.assertEqual(loaded.nb_typed, 3)
        self.assertTrue(loaded.search("car"))
        self.assertTrue(loaded.search("cart"))
        self.assertTrue(loaded.search("dog"))
        self.assertEqual(loaded.get("", n=3), ["dog", "car", "cart"])

if __name__ == "__main__":
    unittest.main()
