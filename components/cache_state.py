#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

# This file contains a basic module that implements the state of an L1 cache
# based on the history of functions whose blocks have traversed it.
# e.g., with the history of F1, F2, F3, F4, the cache's state will be given by
# the union of all those coming before it
from collections import deque

def container_to_cache_size(container):
    return len(container)*4

class FunctionMissModel(object):
    def __init__(self,cache_size,func_worksets,hist_length):
        self.cache_size = cache_size # in B
        self.worksets = func_worksets # dictionary of {f_id : workset} (workset is a list of vaddrs)
        self.hist_length = hist_length
        self.incoming_funcs = deque(maxlen=self.hist_length)
        self.func_history = deque(maxlen=self.hist_length)

    def dispatch(self,func_id):
        self.incoming_funcs.append(func_id)
        assert(len(self.incoming_funcs) <= self.hist_length)

    def func_executed(self,func_id):
        self.func_history.append(func_id)
        if len(self.func_history) > self.hist_length:
            self.func_history.popleft()

    def move_from_inc_to_history(self):
        self.func_history.append(self.incoming_funcs.popleft())
        if len(self.func_history) > self.hist_length:
            self.func_history.popleft()

    # Calculate the union of worksets and overlaps in reverse order starting from the tail of the dispatch q
    def add_to_cache_state(self,cache_state,f_list):
        # Base case: Nothing left in the list of incoming functions OR aggregate size is >= cache size
        if len(f_list) == 0:
            return cache_state
        else:
            f_inc = f_list.pop()
            if container_to_cache_size(cache_state) + container_to_cache_size(self.worksets[f_inc]) >= self.cache_size:
                size_left = self.cache_size - container_to_cache_size(cache_state)
                idx = 0
                while size_left > 0 and idx < len(self.worksets[f_inc]): # add a new element from the new workset repeatedly until filled
                    state_before = len(cache_state)
                    cache_state.add(self.worksets[f_inc][idx])
                    state_after = len(cache_state)
                    if state_before != state_after:
                        size_left -= 4
                    idx += 1
            else:
                # Recursive case: Calculate the union of f_inc with the previous state
                cache_state = set(self.worksets[f_inc]).union(self.add_to_cache_state(cache_state,f_list))
            return cache_state

    def compute_cache_state(self,is_being_executed):
        cache_state = set()
        if is_being_executed:
            self.incoming_funcs.popleft()

        # Account for functions in reverse from the incoming function queue.
        inc_copy = self.incoming_funcs.copy()
        cache_state = self.add_to_cache_state(cache_state,inc_copy)

        if (len(cache_state)*4) < self.cache_size:
            # Add functions from the outgoing function queue if needed.
            hist_copy = self.func_history.copy()
            cache_state = self.add_to_cache_state(cache_state,hist_copy)

        return cache_state

    def get_misses_for_function(self,incoming_func_id,is_being_executed=False):
        # Given a new function, need to compute the pseudo-cache state before determining
        # how many misses it can be expected to incur
        cstate = self.compute_cache_state(is_being_executed)

        # Compute expected misses - set difference of this working set vs cache state ( turn into cb addrs )
        workset_missing = set(self.worksets[incoming_func_id]).difference(cstate)
        cbaddrs = set(map(lambda x : x >> 6,workset_missing))
        return len(cbaddrs) # number of unique cbaddrs
