#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

from numpy.random import exponential
class uServiceFunctionTime(object):
    def __init__(self,fixed_time,workset,lookahead,L1Cache,NumFunctions):
        self.T = fixed_time
        self.W = workset
        self.L = lookahead
        self.S_cache = L1Cache
        self.Nf = NumFunctions

        self.InstWidth = 4 # ARM64, 4 bytes
        self.CBSize = 64
        self.LLCLat = 25 # 50 cycles = 25ns
        self.InstPacking = self.CBSize / self.InstWidth

    def get(self):
        fix = exponential(self.T)

        # Number of expected misses
        prob_miss = 1-min(1,self.S_cache/(self.W * self.Nf))
        num_trials = (float(self.W)/self.InstWidth) / self.InstPacking / (self.L + 1)
        exp_num_misses = prob_miss * num_trials

        return fix + (self.LLCLat * exp_num_misses)
