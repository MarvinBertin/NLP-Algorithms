import math, collections

class LaplaceUnigramLanguageModel:

  def __init__(self, corpus):
    """Initialize your data structures in the constructor."""
    # TODO your code here
    self.LaplaceUnigramCounts = collections.defaultdict(lambda: 1)
    self.total = 0
    self.train(corpus)

  def train(self, corpus):
    """ Takes a corpus and trains your language model. 
        Compute any counts or other corpus statistics in this function.
    """  
    for sentence in corpus.corpus:
        for datum in sentence.data:  
            token = datum.word
            self.LaplaceUnigramCounts[token] += 1
            self.total += 1

  def score(self, sentence):
    """ Takes a list of strings as argument and returns the log-probability of the 
        sentence using your language model. Use whatever data you computed in train() here.
    """
    # TODO your code here
    score = 0.0
    V = len(self.LaplaceUnigramCounts) 

    for token in sentence:
        count = self.LaplaceUnigramCounts[token]
        score += math.log(count)
        score -= math.log(self.total + V)
    return score
