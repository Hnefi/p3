#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
from numpy.random import exponential as exp_arrival
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.store import Store
from .end_measure import EndOfMeasurements
from .requests import RPCRequest

## A class which serves as a Poisson load generator. Assumes lambda = 1.
class PoissonLoadGen(object):
    def __init__(self,simpy_env,out_queue,num_events,key_obj):
        self.env = simpy_env
        self.q = out_queue
        self.num_events = num_events
        self.myLambda = 1.0
        self.key_generator = key_obj
        self.action = self.env.process(self.run())

    def run(self):
        numGenerated = 0
        while numGenerated < self.num_events:
            try:
                req = RPCRequest()
                # TODO: setup parameters like id, key, etc
                yield self.q.put(req)
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
                req = RPCRequest()
                # TODO: setup parameters like id, key, etc
                yield self.q.put(req)
                yield self.env.timeout(exp_arrival(self.myLambda))
            except Interrupt as i:
                print("LoadGenerator killed by feedback with Simpy text:",i)
                return
