#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from .requests import FuncRequest
from .userv_loadgen import uServLoadGen

from random import random
from bisect import bisect_right

## A class which serves as a load generator for a microservice-simulation, with non-uniform
## request types.
class NonUniformUServLoadGen(uServLoadGen):
    def conv_cumulative_vect(self,pvec):
        cumsum = 0
        ovec = []
        for x in pvec:
            cumsum += x
            ovec.append(cumsum)
        return ovec

    def __init__(self,simpy_env,out_queue,num_events,interarrival_time,num_functions,pop_vector):
        super().__init__(simpy_env,out_queue,num_events,interarrival_time,num_functions)
        assert(len(pop_vector) == num_functions)
        self.pop_vector = pop_vector
        self.cvec = self.conv_cumulative_vect(self.pop_vector)

    def gen_new_req(self,rpc_id=-1):
        # Setup parameters id and func_type
        r = random() # standard interval

        f_idx = bisect_right(self.cvec, r)
        if f_idx < len(self.cvec):
            req = FuncRequest(rpc_id,f_idx)
            return req
        raise ValueError('randint() generated',r,'and bisect_right returned idx',f_idx,
                'which is >= than the cdf array\'s length',len(self.cvec))
