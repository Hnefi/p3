#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

from numpy.random import exponential
from math import ceil,floor

from abc import ABC,abstractmethod

# This class calculates its service times uniformly, as a function of
# the num. of functions, and the # of functions that thrash a BTB.
class uServiceFunctionTimeABC(ABC):
    @abstractmethod
    def __init__(self,workset,num_functions,func_thrashing_boundary,library_fraction):
        pass

    @abstractmethod
    def get(self,func_id=0): # base class, all derived classes should override this
        pass

class StaticUServiceTime(uServiceFunctionTimeABC):
    def __init__(self,workset,num_functions,func_thrashing_boundary,library_fraction):
        self.W = workset
        self.Nf = num_functions
        self.func_thrashing_boundary = func_thrashing_boundary
        self.lib_fraction = library_fraction

        # Assumptions: full IPC = 1.2, bb_size = 5
        self.max_cpi = 1/float(1.2)
        self.bb_size = 5
        self.InstWidth = 4 # ARM64, 4 bytes
        self.CBSize = 64
        self.LLCLat = 50 # 50 cycles = 25ns
        self.InstPacking = self.CBSize / self.InstWidth

    def get(self,func_id=0):
        num_insts_private = self.W/self.InstWidth * (1-self.lib_fraction)
        num_insts_lib = self.W/self.InstWidth * self.lib_fraction

        if self.Nf > self.func_thrashing_boundary:
            num_bbs = ceil(float(num_insts_private) / self.bb_size)
            spatial_locality = floor((self.InstPacking - self.bb_size)/self.bb_size)
            num_bb_misses = floor(num_bbs / (1+spatial_locality))
            num_bb_hits = num_bbs - num_bb_misses
            bb_miss_cycles = num_bb_misses * (self.bb_size+self.LLCLat)/self.bb_size * self.max_cpi
            bb_hit_cycles = num_bb_hits * self.bb_size * self.max_cpi
            cycles_private = bb_hit_cycles + bb_miss_cycles

            cycles_lib = num_insts_lib * self.max_cpi
            stime = (cycles_private + cycles_lib)/2
            #print('Service time is',stime,'broken into private=',cycles_private/2,'and lib=',cycles_lib/2)
        else:
            stime = ((self.W/self.InstWidth) * self.max_cpi)/2

        return stime

        #fix = exponential(self.T)
        # Number of expected misses
        #prob_miss = 1-min(1,self.S_cache/(self.W * self.Nf))
        #num_trials = (self.T * 2) / self.InstPacking / (self.L + 1)
        #exp_num_misses = prob_miss * num_trials
        #inst_stalls_cycles = (self.LLCLat * exp_num_misses)

# This class calculates its service times dynamically, to go along with affinity-based
# dispatch. The choice is based on the past N unique functions that were dispatched to
# this class generator. If N is > the thrash-hold, then the func pays a higher cost.
class DynamicUServTime(uServiceFunctionTimeABC):
    def __init__(self,workset,num_functions,func_thrashing_boundary,library_fraction):
        self.W = workset
        self.Nf = num_functions
        self.func_thrashing_boundary = func_thrashing_boundary
        self.lib_fraction = library_fraction

        self.func_history = []

        # Assumptions: full IPC = 1.2, bb_size = 5
        self.max_cpi = 1/float(1.2)
        self.bb_size = 5
        self.InstWidth = 4 # ARM64, 4 bytes
        self.CBSize = 64
        self.LLCLat = 50 # 50 cycles = 25ns
        self.InstPacking = self.CBSize / self.InstWidth

    def get(self,func_id=0):
        num_insts_private = self.W/self.InstWidth * (1-self.lib_fraction)
        num_insts_lib = self.W/self.InstWidth * self.lib_fraction
        if func_id in self.func_history:
            # Pay "fast" cost, BTB resident
            stime = ((self.W/self.InstWidth) * self.max_cpi)/2
            #print('paying fast cost',stime)
            #print('history',self.func_history)
        else:
            # Slow, BTB thrashed
            num_bbs = ceil(float(num_insts_private) / self.bb_size)
            #num_bbs = num_insts_private / self.bb_size
            cycles_private = num_bbs * (self.bb_size+self.LLCLat)/self.bb_size
            cycles_lib = num_insts_lib * self.max_cpi
            stime = (cycles_private + cycles_lib)/2
            #print('paying slow cost',stime)

            # This is a new unique function which will be BTB-tracked. Store in history.
            self.func_history.append(func_id)
            if len(self.func_history) > self.func_thrashing_boundary:
                self.func_history.pop(0)
            #print('history',self.func_history)
        return stime
