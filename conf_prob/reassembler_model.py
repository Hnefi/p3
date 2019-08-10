#!/bin/python3
class Reassembler:
    """ A class modelling an associative hw reassembler unit. """
    self.theSets = -1
    self.theWays = -1
    self.theFAParam = False
    def __init__(self,sets,ways,fa=False):
        self.theSets = sets
        self.theWays = ways
        self.theFAParam = fa
