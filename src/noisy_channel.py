from trie import Trie
import numpy as np


def prior(trie, candidate):
    count_total = trie.nb_typed
    return (candidate[4]+1)/count_total

def editprob(candidate, confusion):
    match candidate[1]:
        case "sub" :
            return confusion.substitute(candidate[2],candidate[3])/confusion.count_bigram(candidate[2],candidate[3])
        case "ins" :
            return confusion.insert(candidate[2],candidate[3])/confusion.count_unigram(candidate[3])
        case "del" :
            return confusion.delete(candidate[2],candidate[3])/confusion.count_unigram(candidate[3])
        case "rev" :
            return confusion.reverse(candidate[2],candidate[3])/confusion.count_bigram(candidate[2],candidate[3])
        case None :
            return confusion.none()
        case _:
            raise KeyError('Error editprob') 

def noisy_channel(word, trie, confusion, n = 10):
    candidates = trie.get_noise(word)
    score = np.zeros(candidates.shape[0])
    for n, c in enumerate(candidates):
        score[n] = np.log(prior(trie, c)) + np.log(editprob(c, confusion))

    score_sorted = np.argsort(score)[::-1][:n]

    return [(candidates[i, 0], score[i]) for i in score_sorted]





