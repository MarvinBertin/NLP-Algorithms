#!/usr/bin/env python
import json
import math
import os
import re
import sys

from PorterStemmer import PorterStemmer
from collections import defaultdict, Counter
import numpy as np

class IRSystem:

    def __init__(self):
        # For holding the data - initialized in read_data()
        self.titles = []
        self.docs = []
        self.vocab = []
        # For the text pre-processing.
        self.alphanum = re.compile('[^a-zA-Z0-9]')
        self.p = PorterStemmer()


    def get_uniq_words(self):
        uniq = set()
        for doc in self.docs:
            uniq.update(doc)
        return uniq


    def __read_raw_data(self, dirname):
        print "Stemming Documents..."

        titles = []
        docs = []
        os.mkdir('%s/stemmed' % dirname)
        title_pattern = re.compile('(.*) \d+\.txt')

        # make sure we're only getting the files we actually want
        filenames = []
        for filename in os.listdir('%s/raw' % dirname):
            if filename.endswith(".txt") and not filename.startswith("."):
                filenames.append(filename)

        for i, filename in enumerate(filenames):
            title = title_pattern.search(filename).group(1)
            print "    Doc %d of %d: %s" % (i+1, len(filenames), title)
            titles.append(title)
            contents = []
            f = open('%s/raw/%s' % (dirname, filename), 'r')
            of = open('%s/stemmed/%s.txt' % (dirname, title), 'w')
            for line in f:
                # make sure everything is lower case
                line = line.lower()
                # split on whitespace
                line = [xx.strip() for xx in line.split()]
                # remove non alphanumeric characters
                line = [self.alphanum.sub('', xx) for xx in line]
                # remove any words that are now empty
                line = [xx for xx in line if xx != '']
                # stem words
                line = [self.p.stem(xx) for xx in line]
                # add to the document's conents
                contents.extend(line)
                if len(line) > 0:
                    of.write(" ".join(line))
                    of.write('\n')
            f.close()
            of.close()
            docs.append(contents)
        return titles, docs


    def __read_stemmed_data(self, dirname):
        print "Already stemmed!"
        titles = []
        docs = []

        # make sure we're only getting the files we actually want
        filenames = []
        for filename in os.listdir('%s/stemmed' % dirname):
            if filename.endswith(".txt") and not filename.startswith("."):
                filenames.append(filename)

        if len(filenames) != 60:
            msg = "There are not 60 documents in ../data/RiderHaggard/stemmed/\n"
            msg += "Remove ../data/RiderHaggard/stemmed/ directory and re-run."
            raise Exception(msg)

        for i, filename in enumerate(filenames):
            title = filename.split('.')[0]
            titles.append(title)
            contents = []
            f = open('%s/stemmed/%s' % (dirname, filename), 'r')
            for line in f:
                # split on whitespace
                line = [xx.strip() for xx in line.split()]
                # add to the document's conents
                contents.extend(line)
            f.close()
            docs.append(contents)

        return titles, docs


    def read_data(self, dirname):
        """
        Given the location of the 'data' directory, reads in the documents to
        be indexed.
        """
        # NOTE: We cache stemmed documents for speed
        #       (i.e. write to files in new 'stemmed/' dir).

        print "Reading in documents..."
        # dict mapping file names to list of "words" (tokens)
        filenames = os.listdir(dirname)
        subdirs = os.listdir(dirname)
        if 'stemmed' in subdirs:
            titles, docs = self.__read_stemmed_data(dirname)
        else:
            titles, docs = self.__read_raw_data(dirname)

        # Sort document alphabetically by title to ensure we have the proper
        # document indices when referring to them.
        ordering = [idx for idx, title in sorted(enumerate(titles),
            key = lambda xx : xx[1])]

        self.titles = []
        self.docs = []
        numdocs = len(docs)
        for d in range(numdocs):
            self.titles.append(titles[ordering[d]])
            self.docs.append(docs[ordering[d]])

        # Get the vocabulary.
        self.vocab = [xx for xx in self.get_uniq_words()]


    def compute_tfidf(self):
        # Compute and store TF-IDF values for words and documents.

        print "Calculating tf-idf..."

        self.tfidf = defaultdict(lambda: defaultdict(float))
        N = len(self.docs)

        self.idf = {word: np.log10(N / float(len(self.get_posting(word)))) 
                    for word in self.vocab}

        for idx, doc in enumerate(self.docs):
            word_counts = Counter(doc)
            for word in word_counts:
                num = word_counts[word]
                if num:
                    self.tfidf[word][idx] = (1 + np.log10(num)) * self.idf[word]
                

    def get_tfidf(self, word, document):
        # Return the tf-idf weigthing for the given word (string) and
        #       document index.

        #print word, self.tfidf[word][document]
        return self.tfidf[word][document]


    def get_tfidf_unstemmed(self, word, document):
        """
        This function gets the TF-IDF of an *unstemmed* word in a document.
        Stems the word and then calls get_tfidf. You should *not* need to
        change this interface, but it is necessary for submission.
        """
        word = self.p.stem(word)
        return self.get_tfidf(word, document)


    def index(self):
        """
        Build an index of the documents.
        """
        print "Indexing..."
        # Create an inverted index.

        self.inv_index = defaultdict(set)
        for idx, doc in enumerate(self.docs):
            for word in set(doc):
                self.inv_index[word].add(idx)


    def get_posting(self, word):
        """
        Given a word, this returns the list of document indices (sorted) in
        which the word occurs.
        """
        return self.inv_index[word]


    def get_posting_unstemmed(self, word):
        """
        Given a word, this *stems* the word and then calls get_posting on the
        stemmed word to get its postings list. You should *not* need to change
        this function. It is needed for submission.
        """
        word = self.p.stem(word)
        return self.get_posting(word)


    def boolean_retrieve(self, query):
        """
        Given a query in the form of a list of *stemmed* words, this returns
        the list of documents in which *all* of those words occur (ie an AND
        query).
        Return an empty list if the query does not return any documents.
        """
        return reduce(lambda a, b: a & b,
                  map(lambda word: self.get_posting_unstemmed(word), query))


    def rank_retrieve(self, query):
        """
        Given a query (a list of words), return a rank-ordered list of
        documents (by ID) and score for the query.
        """

        scores = np.zeros(len(self.docs))

        for word in query:
            q_tfidf = 1 + np.log10(query.count(word))
            for idx in self.get_posting(word):
                d_tfidf = self.get_tfidf(word, idx)
                scores[idx] += q_tfidf * d_tfidf


        for idx, score in enumerate(scores):
            doc_tfidf = np.array([self.tfidf[word][idx] for word in set(self.docs[idx])])
            scores[idx] /= np.linalg.norm(doc_tfidf)

        # Jaccard Distance
        # for d, doc in enumerate(self.docs):
        #     words_in_doc = set(doc)
        #     scores[d] = len(words_in_query.intersection(words_in_doc)) \
        #             / float(len(words_in_query.union(words_in_doc)))
        # ranking = [idx for idx, sim in sorted(enumerate(scores),
        #     key = lambda xx : xx[1], reverse = True)]

        #map(lambda i: (ranking[i], scores[ranking[i]]), range(10))
        return sorted(list(enumerate(scores)), key=lambda t: t[1], reverse=True)[:10]

    def process_query(self, query_str):
        """
        Given a query string, process it and return the list of lowercase,
        alphanumeric, stemmed words in the string.
        """
        # make sure everything is lower case
        query = query_str.lower()
        # split on whitespace
        query = query.split()
        # remove non alphanumeric characters
        query = [self.alphanum.sub('', xx) for xx in query]
        # stem words
        query = [self.p.stem(xx) for xx in query]
        return query


    def query_retrieve(self, query_str):
        """
        Given a string, process and then return the list of matching documents
        found by boolean_retrieve().
        """
        query = self.process_query(query_str)
        return self.boolean_retrieve(query)


    def query_rank(self, query_str):
        """
        Given a string, process and then return the list of the top matching
        documents, rank-ordered.
        """
        query = self.process_query(query_str)
        return self.rank_retrieve(query)


def run_tests(irsys):
    print "===== Running tests ====="

    ff = open('../data/queries.txt')
    questions = [xx.strip() for xx in ff.readlines()]
    ff.close()
    ff = open('../data/solutions.txt')
    solutions = [xx.strip() for xx in ff.readlines()]
    ff.close()

    epsilon = 1e-4
    for part in range(4):
        points = 0
        num_correct = 0
        num_total = 0

        prob = questions[part]
        soln = json.loads(solutions[part])

        if part == 0:     # inverted index test
            print "Inverted Index Test"
            words = prob.split(", ")
            for i, word in enumerate(words):
                num_total += 1
                posting = irsys.get_posting_unstemmed(word)
                if set(posting) == set(soln[i]):
                    num_correct += 1

        elif part == 1:   # boolean retrieval test
            print "Boolean Retrieval Test"
            queries = prob.split(", ")
            for i, query in enumerate(queries):
                num_total += 1
                guess = irsys.query_retrieve(query)
                if set(guess) == set(soln[i]):
                    num_correct += 1

        elif part == 2:   # tfidf test
            print "TF-IDF Test"
            queries = prob.split("; ")
            queries = [xx.split(", ") for xx in queries]
            queries = [(xx[0], int(xx[1])) for xx in queries]
            for i, (word, doc) in enumerate(queries):
                num_total += 1
                guess = irsys.get_tfidf_unstemmed(word, doc)
                if guess >= float(soln[i]) - epsilon and \
                        guess <= float(soln[i]) + epsilon:
                    num_correct += 1

        elif part == 3:   # cosine similarity test
            print "Cosine Similarity Test"
            queries = prob.split(", ")
            for i, query in enumerate(queries):
                num_total += 1
                ranked = irsys.query_rank(query)
                top_rank = ranked[0]
                if top_rank[0] == soln[i][0]:
                    if top_rank[1] >= float(soln[i][1]) - epsilon and \
                            top_rank[1] <= float(soln[i][1]) + epsilon:
                        num_correct += 1

        feedback = "%d/%d Correct. Accuracy: %f" % \
                (num_correct, num_total, float(num_correct)/num_total)
        if num_correct == num_total:
            points = 3
        elif num_correct > 0.75 * num_total:
            points = 2
        elif num_correct > 0:
            points = 1
        else:
            points = 0

        print "    Score: %d Feedback: %s" % (points, feedback)


def main(args):
    irsys = IRSystem()
    irsys.read_data('../data/RiderHaggard')
    irsys.index()
    irsys.compute_tfidf()


    if len(args) == 0:
        run_tests(irsys)
    else:
        query = " ".join(args)
        print "Best matching documents to '%s':" % query
        results = irsys.query_rank(query)
        for docId, score in results:
            print "%s: %e" % (irsys.titles[docId], score)


if __name__ == '__main__':
    args = sys.argv[1:]
    main(args)
