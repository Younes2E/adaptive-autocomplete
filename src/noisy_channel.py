from trie import Trie
import numpy as np

def prior(trie, candidate):
    count_total = trie.nb_typed
    return (candidate[4]+1)/count_total

def editprob(candidate, confusion):
    delta = 0.5
    match candidate[1]:
        case "sub" :
            return (confusion.substitute(candidate[2],candidate[3])+delta)/(confusion.count_unigram(candidate[3])+ delta * 26)
        case "ins" :
            return (confusion.insert(candidate[2],candidate[3])+delta)/(confusion.count_unigram(candidate[3])+ delta * 26)
        case "del" :
            return (confusion.delete(candidate[2],candidate[3])+delta)/(confusion.count_bigram(candidate[2],candidate[3])+ delta * 26)
        case "rev" :
            return (confusion.reverse(candidate[2],candidate[3])+delta)/(confusion.count_bigram(candidate[2],candidate[3])+ delta * 26)
        case None :
            return 0.9
        case _:
            raise KeyError('Error editprob') 

def noisy_channel(word, trie, confusion, n = 10):
    candidates = trie.get_noise(word)
    score = np.zeros(len(candidates))
    for idx, c in enumerate(candidates):
        score[idx] = np.log(prior(trie, c)) + np.log(editprob(c, confusion))

    score_sorted = np.argsort(score)[::-1]
    
    return np.array([(candidates[i][0], score[i]) for i in score_sorted[:n]])





