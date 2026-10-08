import numpy as np
from utils import softmax

def prior(trie, candidate):
    count_total = trie.nb_typed
    return (candidate[4]+1)/count_total

def editprob(candidate, confusion):
    delta = 0.5
    _, op, x, w = candidate[:4]
    match op:
        case "sub":
            return (confusion.substitute(w, x) + delta)/(confusion.count_unigram(x)+delta*26)
        case "ins":
            return (confusion.insert(x, w) + delta)/(confusion.count_unigram(x)+delta*26)
        case "del":
            return (confusion.delete(x, w) + delta)/(confusion.count_bigram(x, w)+delta*26)
        case "rev":
            return (confusion.reverse(x, w) + delta)/(confusion.count_bigram(x, w)+delta*26)
        case None:
            return 0.9 
        case _:
            raise KeyError(f'operation inconnue : {op}')

def noisy_channel(word, trie, confusion, n=20, distance=1, max_depth=3):
    candidates = trie.get_noise(word, distance, max_depth)
    if not candidates:
        return []
    score = np.zeros(len(candidates))
    for idx, c in enumerate(candidates):
        score[idx] = np.log(prior(trie, c)) + np.log(editprob(c, confusion))
    score_softmax = softmax(score)
    score_sorted = np.argsort(score_softmax)[::-1]

    return [(candidates[i][0], score_softmax[i]) for i in score_sorted[:n]]
