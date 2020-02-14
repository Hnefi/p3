#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
## A class which returns integer values (TODO: variable length strings)
## distributed according to a parameterized zipf distribution.
#from math import pow

class ZipfGenerator(object):
    def calc_generalized_harmonic(self,n,power=1):
        harm = 0.0
        for i in range(n):
            harm += (1.0 / (float(i+1)**power))
        return harm

    def init_harmonics(self):
        size = int(self.theConfig['N'])
        s = float(self.theConfig['s'])

        self.harmonic = self.calc_generalized_harmonic(size,s)
        self.harm_array = [ (1.0 / pow(i+1,s))/self.harmonic for i in range(size) ]

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
        print('Initializing harmonic sums...',end=' ')
        self.init_harmonics()
        print('Done!')

    def prob_for_rank(self,k):
        s = float(self.theConfig['s'])
        return ( (float(1.0)/pow(k,s)) / (self.harmonic) )

    def get_new_int(self):
        pass
