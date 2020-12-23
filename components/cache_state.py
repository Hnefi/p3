#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

# This file contains a basic module that implements the state of an L1 cache
# based on the history of functions whose blocks have traversed it.
# e.g., with the history of F1, F2, F3, F4, the cache's state will be given by
# W1 + (W2-s12) + (W3-s12-s13) + (W4-s12-s13-14)
# where sij is the shared code overlap between those functions
from collections import deque

class FunctionMissModel(object):
    def __init__(self,cache_size,func_worksets,code_overlaps,hist_length):
        self.cache_size = cache_size # in KB
        self.worksets = func_worksets # dictionary of {f_id : workset} (in KB)
        self.sharing_fractions = code_overlaps # list of lists, where sharing_fractions[i][j] is the
                                               # amount of code (in KB) shared between i & j
        self.hist_length = hist_length
        self.incoming_funcs = deque(maxlen=self.hist_length)
        self.func_history = deque(maxlen=self.hist_length)

    def dispatch(self,func_id):
        if len(self.incoming_funcs) >= self.hist_length:
            self.func_history.append(self.incoming_funcs.popleft())
        self.incoming_funcs.append(func_id)

    def add_to_cache_state(self,agg_size,funcs_in_cache,f_list):
        inc_copy = f_list.copy()
        while len(inc_copy) > 0 and agg_size <= self.cache_size:
            f_inc = inc_copy.pop()
            size_to_add = self.worksets[f_inc]
            for prev_function in funcs_in_cache:
                # Subtract the common workset between this new one and all previous ones
                print('subtracting shared code of',self.sharing_fractions[f_inc][prev_function],'from size of',size_to_add)
                size_to_add -= self.sharing_fractions[f_inc][prev_function]
                assert(size_to_add >= 0) # Assume a functions' code cannot 100% overlap with other ones.
            agg_size += size_to_add
            funcs_in_cache.append(f_inc)
            print('incoming func was',f_inc,'adding',size_to_add,'to the aggregate for a total of',agg_size)
        return agg_size, funcs_in_cache

    def compute_cache_state(self):
        aggregate_size = 0
        funcs_in_cache = []
        # Account for functions in reverse from the incoming function queue.
        aggregate_size, funcs_in_cache = add_to_cache_state(aggregate_size,funcs_in_cache,self.incoming_funcs)

        # If still not enough, add functions from the outgoing function queue
        aggregate_size, funcs_in_cache = add_to_cache_state(aggregate_size,funcs_in_cache,self.func_history)

        return funcs_in_cache

    def get_misses_for_function(self,incoming_func_id):
        # Given a new function, need to compute the pseudo-cache state before determining
        # how many misses it can be expected to incur

        libs_present = compute_cache_state()

        # Compute expected misses - expect that all libraries this function shares with those IN
        # the cache already will be hits. All else will be misses.
        workset_present = sum(list(map(lambda x : self.sharing_fractions[incoming_func_id][x], libs_present)))
        workset_missing = self.worksets[incoming_func_id] - workset_present

        return workset_missing / 64 # divide by cb size
