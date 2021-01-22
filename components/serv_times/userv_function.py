#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

from numpy.random import exponential
from math import ceil,floor
from abc import ABC,abstractmethod

from ..cache_state import FunctionMissModel

# This class calculates its service times uniformly, as a function of
# the num. of functions, and the # of functions that thrash a BTB.
class uServiceFunctionTimeABC(ABC):
    @abstractmethod
    def __init__(self,workset,num_functions,func_thrashing_boundary,library_fraction):
        pass

    @abstractmethod
    def get(self,func_id=0): # base class, all derived classes should override this
        pass

class WSetVariedServiceTime(uServiceFunctionTimeABC):
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

# This class calculates its service times dynamically, to go along with affinity-based
# dispatch. The service time is based on the FunctionMissModel cache state tracker.
class DynamicUServTime(uServiceFunctionTimeABC):
    def __init__(self,func_worksets,cache_size,hist_length):
        self.working_sets = func_worksets
        self.cache_size = cache_size # in B
        self.MissPredictor = FunctionMissModel(cache_size,func_worksets,hist_length)

        # Assumptions: full IPC = 1.2, bb_size = 5
        self.max_cpi = 1/float(1.2)
        self.bb_size = 5
        self.InstWidth = 4 # ARM64, 4 bytes
        self.CBSize = 64
        self.LLCLat = 50 # 50 cycles = 25ns
        self.InstPacking = self.CBSize / self.InstWidth

    def new_dispatch(self,func_id):
        self.MissPredictor.dispatch(func_id)

    def func_executed(self,func_id):
        self.MissPredictor.func_executed(func_id)

    def get(self,func_id):
        # Function service time is constant CPI + cost of L1 misses
        num_insts = len(self.working_sets[func_id])
        cpu_exec_cycles = num_insts * self.max_cpi;
        miss_cycles = self.MissPredictor.get_misses_for_function(func_id,is_being_executed=True) * self.LLCLat
        #print('service time being returned is',cpu_exec_cycles,'plus',miss_cycles)
        return cpu_exec_cycles + miss_cycles

        # This is a new unique function which will be BTB-tracked. Store in history.
        #self.func_history.append(func_id)
        #if len(self.func_history) > self.func_thrashing_boundary:
            #self.func_history.pop(0)
        #print('history',self.func_history)
