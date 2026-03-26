import json

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False
        self.freq = 0
        self.nb_used = 0

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def add(self, word: str, freq: int = 0):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_word = True
        node.freq = freq

    def remove(self, word: str):
        node = self.root
        for char in word :  
            if char not in node.children : 
                print('unable to remove word, not in trie')
                return 
            node = node.children[char]
        node.is_word = False

    def use(self, word: str):
        if self.search(word) : 
            node = self.root
            for char in word : 
                node = node.children[char]
            node.nb_used += 1
        else : 
            print('unable to use word, not in trie')

    def search(self, word: str) -> bool:
        node = self.root
        for char in word : 
            if char not in node.children : 
                return False 
            node = node.children[char]
        return node.is_word 

    def get(self, prefix: str, n: int = 5, max_depth: int = 5):
        res = []
        node = self.root 
        for char in prefix :
            if char not in node.children : 
                return []
            node = node.children[char]
        
        def dfs(current_node, current_word, current_depth):
            if current_node.is_word:
                res.append((current_word, current_node.freq + current_node.nb_used))
            
            if current_depth == max_depth:
                return 
            
            for char, child_node in current_node.children.items():
                dfs(child_node, current_word + char, current_depth + 1)
            
        dfs(node, prefix, 0)
        
        res.sort(key=lambda x: x[1], reverse=True)
        return [word for word, score in res[:n]]

        
        


    def save(self, path: str):
        # TODO: Save trie to a JSON file
        pass

    def load(self, path: str):
        # TODO: Load trie from a JSON file
        pass
