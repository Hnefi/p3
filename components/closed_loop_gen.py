#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.store import Store
from .end_measure import EndOfMeasurements
from .requests import FuncRequestWithServTime, PullFeedbackRequest
from .load_generator import AbstractLoadGen

from random import randint
from csv import DictReader

## A class which serves as a closed-loop load generator for a microservice-simulation
## where all of the following are file-specified: function ids, interarrival times, serv. times
class ClosedLoopLoadGen(AbstractLoadGen):
    def __init__(self,simpy_env,out_queue,func_file):
        super().__init__()
        self.env = simpy_env
        self.ffile = func_file
        self.q = out_queue
        self.action = self.env.process(self.run())

    def set_core(self,core):
        # Will inform core of function dispatch if not None
        # for purposes of queue state tracking
        self.core_to_inform = core

    def gen_new_req(self,req_num,row):
        return FuncRequestWithServTime(req_num,row['f_type'],row['serv_time'])

    def next_interarrival(self,row):
        return row['int_time']

    def run(self):
        numGenerated = 0
        row = {'f_type': 0,
               'serv_time' : 100,
               'int_time': 200 }  # compatible w. DictReader API
        while numGenerated < 10:
            # Wait until the server sends a pull
            req_ack = yield self.q.get()
            assert(isinstance(req_ack,PullFeedbackRequest) is True)

            req = self.gen_new_req(numGenerated,row)
            req.dispatch_time = self.env.now

            # Now put a new request (the gen_new_req comes from the superclass)
            if self.core_to_inform is not None:
                self.core_to_inform.new_dispatch(req.getFuncType())

            yield self.q.put(req)
            numGenerated += 1
        # Make a new EndOfMeasurements event (special)
        yield self.q.put(EndOfMeasurements())
'''
    def run(self):
        numGenerated = 0
        with open(self.ffile,'r') as fh:
            f_reader = reader(fh) #TODO Convert to DictReader
            for row in f_reader:
                # Wait until the server sends a pull
                req_ack = yield out_queue.get()
                assert(isinstance(req_ack,PullFeedbackRequest) is True)

                # Now put a new request (the gen_new_req comes from the superclass)
                yield self.q.put(self.gen_new_req(numGenerated,row))
                yield self.env.timeout(self.next_interarrival(row))
                numGenerated += 1
'''

