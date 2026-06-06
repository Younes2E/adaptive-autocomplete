import numpy as np

def softmax(x):
    return np.exp(x)/sum(np.exp(x))

def truncate_proba(p, decimals=2):
    n_zeros = max(0, int(-np.floor(np.log10(p))-1))
    n_decimals = max(decimals, n_zeros+2)
    factor = 10 ** n_decimals
    return np.floor(p * factor)/factor