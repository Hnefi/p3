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

class AffinityDispatch(object):
    def __init__(self,qs,history_length,max_len):
        self.queues = qs
        self.histories = [[] for q in range(len(self.queues))]
        self.history_length = history_length
        self.max_affinity_q_len = max_len

    def qs_with_target_function(self,func_id):
        retlist = []
        for idx in range(len(self.queues)):
            if func_id in self.histories[idx]:
                retlist.append(idx)
        return retlist

    def select(self,req):
        queues_with_history = self.qs_with_target_function(req.getFuncType())
        #print('---- NEW REQ w. TYPE ------',req.getFuncType())
        if len(queues_with_history) == 0:
            final_queue, unfilt_len = find_shortest_q(self.queues)
            #print('final choice LBALANCE:',final_queue)
        else:
            shortest_q_index_filtered,filt_len = find_shortest_q(self.queues,filter_list=queues_with_history)
            shortest_q_index,unfilt_len = find_shortest_q(self.queues)
            #print('Shortest q index w. function filter:',shortest_q_index_filtered,'len',filt_len,'global shortest q:',shortest_q_index,'len',unfilt_len)

            if filt_len >= self.max_affinity_q_len: # past static q length, pick global shortest
                final_queue = shortest_q_index
                #print('final choice LBALANCE:',final_queue)
            else:
                final_queue = shortest_q_index_filtered # return the shortest among those with history
                #print('final choice AFFINITY:',final_queue)

        # push this func type into the appropriate history
        self.histories[final_queue].append(req.getFuncType())
        if len(self.histories[final_queue]) > self.history_length:
            self.histories[final_queue].pop(0) # remove head

        return final_queue
