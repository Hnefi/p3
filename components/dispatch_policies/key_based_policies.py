#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from my_simpy.src.simpy.resources.store import Store
from base_policies import find_shortest_q

# Python base package includes
from random import randint

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
