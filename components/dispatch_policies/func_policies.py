#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from my_simpy.src.simpy.resources.store import Store
from .base_policies import find_shortest_q

# Python base package includes
from random import randint

class FunctionDispatch(object):
    def __init__(self,qs,func_grouping):
        self.queues = qs
        self.func_grouping = func_grouping

    def select(self,req):
        # Map function idx to q
        q_idx = int(req.getFuncType() / self.func_grouping)
        return q_idx

# This dispatch policy implements 'shortest service time' dispatch, with oracle
# knowledge of the service time generator objects. Queueing not taken into account.
class SSTDispatch(object):
    def __init__(self,qs):
        self.queues = qs

    def set_stime_objects(self,stime_objects):
        self.stime_generators = stime_objects

    def select(self,req):
        shortest_time = 1000000000
        shortest_q = 0
        for qdx in range(len(self.stime_generators)):
            t = self.stime_generators[qdx].peek_stime(req.getFuncType())
            if t < shortest_time:
                shortest_time = t
                shortest_q = qdx

        return shortest_q

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
