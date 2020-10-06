#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
## A class which returns integer values (TODO: variable length strings)
## distributed according to a uniform distribution.
from random import seed,uniform
from math import ceil

class UniformKeyGenerator(object):
    def __init__(self,**kwargs):
        # args needed from higher level:
        #   (num_items) -> Number of items in the dataset
        req_args = ['num_items']
        for k in req_args:
            if k not in kwargs.keys():
                raise ValueError("Required",k,"argument not specified in UniformGenerator init")

        self.theConfig = { "N": kwargs["num_items"]
                         }
        self.theNumKeys = int(self.theConfig['N'])
        rand_seed = '0xdeadbeef'
        print('Seeding random with',rand_seed)
        seed(rand_seed)
        print('Done!')

    def get_key(self):
        # Algorithm: Get a random number in the specified interval, return that key rank.
        r = ceil(uniform(0,self.theNumKeys))
        return r
