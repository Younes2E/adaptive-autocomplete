from trie import Trie
import numpy as np

def prior(trie, candidate):
    count_total = trie.nb_typed
    return (candidate[4]+1)/count_total

def editprob(candidate, confusion):
    delta = 0.5
    op = candidate[1] 
    x = candidate[2]
    w = candidate[3]
    match op:
        case "sub" :
            return (confusion.substitute(w, x) + delta)/(confusion.count_unigram(x)+delta*26)
        case "ins" :
            return (confusion.insert(x, w) + delta)/(confusion.count_unigram(x)+delta*26)
        case "del" :
            return (confusion.delete(x, w) + delta)/(confusion.count_bigram(x, w)+delta *26)        
        case "rev" :
            return (confusion.reverse(x, w) + delta)/(confusion.count_bigram(x, w)+delta*26)        
        case None :
            return 0.9
        case _:
            raise KeyError('Error editprob') 

def noisy_channel(word, trie, confusion, n = 20):
    candidates = trie.get_noise(word)
    score = np.zeros(len(candidates))
    for idx, c in enumerate(candidates):
        score[idx] = np.log(prior(trie, c)) + np.log(editprob(c, confusion))

    score_sorted = np.argsort(score)[::-1]
    
    return np.array([(candidates[i][0], score[i]) for i in score_sorted[:n]])





