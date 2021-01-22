#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from my_simpy.src.simpy.resources.store import Store

# Python base package includes
from random import randint

def find_shortest_q(qs,filter_list=None):
    smallest = 1000000000
    shortest_q = 0
    if filter_list is not None:
        for qdx in range(len(qs)):
            if qdx in filter_list:
                c_len = len(qs[qdx].items)
                if c_len < smallest:
                    smallest = c_len
                    shortest_q = qdx
    else:
        for qdx in range(len(qs)):
            c_len = len(qs[qdx].items)
            if c_len < smallest:
                smallest = c_len
                shortest_q = qdx

    return shortest_q,smallest

class RandomDispatchPolicy(object):
    def __init__(self,num_queues):
        self.num_queues = num_queues

    def select(self,req=None):
        the_q_idx = randint(0,self.num_queues-1)
        return the_q_idx

class JSQDispatchPolicy(object):
    def __init__(self,qs):
        self.queues = qs

    def select(self,req=None):
        return find_shortest_q(self.queues)

class JBSQDispatchPolicy(object):
    def __init__(self,qs,bound):
        self.queues = qs
        self.depth_limit = bound

    def select(self,req=None):
        shortest_q = find_shortest_q(self.queues)
        if len(self.queues[shortest_q].items) <= self.depth_limit:
            return shortest_q
        else:
            return -1
