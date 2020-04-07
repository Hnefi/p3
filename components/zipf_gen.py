#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
## A class which returns integer values (TODO: variable length strings)
## distributed according to a parameterized zipf distribution.
from random import random
from bisect import bisect_right

class ZipfKeyGenerator(object):
    def calc_generalized_harmonic(self,n,power=1):
        harm = 0.0
        for i in range(n):
            harm += ( 1.0 / (pow(float(i+1),power)) )
        return harm

    def make_pdf_cdf_arrays(self):
        size = int(self.theConfig['N'])
        s = float(self.theConfig['s'])
        self.pdf_array = [ ]
        self.cdf_array = [ ]
        run_sum = 0.0
        for i in range(size):
            cur_rank_val = (1.0 / pow(i+1,s))/self.harmonic
            run_sum += cur_rank_val
            self.pdf_array.append(cur_rank_val)
            self.cdf_array.append(run_sum)

    def init_harmonics(self):
        size = int(self.theConfig['N'])
        s = float(self.theConfig['s'])
        self.harmonic = self.calc_generalized_harmonic(size,s)

    def __init__(self,**kwargs):
        # args needed from higher level:
        #   (num_items) -> Number of items in the dataset
        #   (coeff) -> Zipf coefficient
        req_args = ['num_items', 'coeff']
        for k in req_args:
            if k not in kwargs.keys():
                raise ValueError("Required",k,"argument not specified in ZipfGenerator init")

        self.theConfig = { "N": kwargs["num_items"],
                            "s": kwargs["coeff"]
                         }
        print('Initializing harmonic sums...')
        self.init_harmonics()
        print('Initializing pdf and cdf arrays....')
        self.make_pdf_cdf_arrays()
        print('Done!')

    def prob_for_rank(self,k):
        return self.pdf_array[k]
        #s = float(self.theConfig['s'])
        #return ( (float(1.0)/pow(k,s)) / (self.harmonic) )

    def get_key(self):
        # Algorithm: Get a random number in the standard interval
        # Fit it into the cdf previously generated, and return the integer describing its rank
        r = random()
        rank = bisect_right(self.cdf_array, r)
        if rank < len(self.cdf_array):
            return rank
        raise ValueError('rand() generated',r,'and bisect_right returned rank',rank,
                'which is >= than the cdf array\'s length',len(self.cdf_array))
