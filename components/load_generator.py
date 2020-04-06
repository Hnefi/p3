#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from numpy.random import exponential as exp_arrival
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.store import Store
from .end_measure import EndOfMeasurements
from .requests import RPCRequest

# Python base package includes
from random import randint

## A class which serves as a Poisson load generator.
class PoissonLoadGen(object):
    def __init__(self,simpy_env,out_queue,num_events,key_obj,incoming_load_A,writes):
        self.env = simpy_env
        self.q = out_queue
        self.num_events = num_events
        self.myLambda = 1/float(incoming_load_A)
        self.key_generator = key_obj
        self.write_frac = writes
        self.action = self.env.process(self.run())

    def gen_new_req(self,rpc_id=-1):
        # Setup parameters like id, key, etc
        req = RPCRequest(rpc_id,self.key_generator.get_key())
        write_integer = randint(0,100)
        if write_integer <= self.write_frac:
            req.setWrite()
        return req

    def run(self):
        numGenerated = 0
        while numGenerated < self.num_events:
            try:
                yield self.q.put(self.gen_new_req(numGenerated))
                yield self.env.timeout(exp_arrival(self.myLambda))
                numGenerated += 1
            except Interrupt as i:
                print("LoadGenerator killed during event generation. Interrupt:",i,"die....")
                return

        # Make a new EndOfMeasurements event (special)
        yield self.q.put(EndOfMeasurements())

        # Keep generating events for realistic measurement
        while True:
            try:
                yield self.q.put(self.gen_new_req(-1))
                yield self.env.timeout(exp_arrival(self.myLambda))
            except Interrupt as i:
                print("LoadGenerator killed by feedback with Simpy text:",i)
                return
