#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from my_simpy.src.simpy.resources.store import Store

# Python base package includes
from random import randint

def find_shortest_q(qs):
    smallest = 1000000000
    shortest_q = 0
    for qdx in range(len(qs)):
        c_len = len(qs[qdx].items)
        if c_len < smallest:
            smallest = c_len
            shortest_q = qdx

    return shortest_q

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

class CREWDispatchPolicy(object):
    def __init__(self,qs):
        self.queues = qs

    def select(self,req):
        if req.getWrite(): # have to go to a single queue
            # Map key to partition/queue.
            # Important not just to take mod of integer key, would result in all hot keys grouping up
            return hash(req.key) % len(self.queues)
        else: # Can dispatch to shortest queue
            return find_shortest_q(self.queues)

class EREWDispatchPolicy(object):
    def __init__(self,qs):
        self.queues = qs

    def select(self,req):
        # Map key to partition/queue.
        # Important not just to take mod of integer key, would result in all hot keys grouping up
        return hash(req.key) % len(self.queues)

class FunctionDispatch(object):
    def __init__(self,qs,func_grouping):
        self.queues = qs
        self.func_grouping = func_grouping

    def select(self,req):
        # Map function idx to q
        q_idx = int(req.getFuncType() / self.func_grouping)
        return q_idx

