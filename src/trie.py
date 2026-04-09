import json

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

    def search(self, word):
        node = self.root
        for char in word : 
            if char not in node.children : 
                return False 
            node = node.children[char]
        return node.is_word 


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

    def get(self, prefix: str, n: int = 5, max_depth: int = 5):
        res = []
        node = self.root 
        for char in prefix :
            if char not in node.children : 
                return []
            node = node.children[char]
        
        def dfs(current_node, current_word, current_depth):
            if current_node.is_word:
                res.append((current_word, current_node.freq + current_node.last_used))
            
            if current_depth == max_depth:
                return 
            
            for char, child_node in current_node.children.items():
                dfs(child_node, current_word + char, current_depth + 1)
            
        dfs(node, prefix, 0)
        
        res.sort(key=lambda x: x[1], reverse=True)
        return [word for word, score in res[:n]]

    def save(self, path: str):
        def serialize(node):
            return {
                "is_word": node.is_word,
                "freq": node.freq,
                "last_used": node.last_used,
                "children": {
                    char: serialize(child)
                    for char, child in node.children.items()
                },
            }
        data = {
            "nb_typed": self.nb_typed,
            "root": serialize(self.root),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


    def load(self, path: str):
        def deserialize(data):
            node = TrieNode()
            node.is_word = data["is_word"]
            node.freq = data["freq"]
            node.last_used = data["last_used"]
            node.children = {char: deserialize(child) for char, child in data["children"].items()}
            return node
        with open(path, "r") as f:
            data = json.load(f)
            self.nb_typed = data["nb_typed"]
            self.root = deserialize(data["root"]) 
        return self
    
    def load_dict(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    word = parts[0].lower()
                    try:
                        frequency = int(parts[1])
                        self.add(word, freq = frequency)
                    except Exception:
                        continue

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