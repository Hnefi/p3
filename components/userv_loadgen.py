#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from numpy.random import exponential as exp_arrival
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.store import Store
from .end_measure import EndOfMeasurements
from .requests import FuncRequest
from .load_generator import AbstractLoadGen

from random import randint

## A class which serves as a load generator for a microservice-simulation with multiple req types.
class uServLoadGen(AbstractLoadGen):
    def __init__(self,simpy_env,out_queue,num_events,interarrival_time,num_functions):
        super().__init__()
        self.env = simpy_env
        self.q = out_queue
        self.num_events = num_events
        self.myLambda = interarrival_time
        self.num_functions = num_functions
        self.action = self.env.process(self.run())

    def gen_new_req(self,rpc_id=-1):
        # Setup parameters id and func_type
        f_type = randint(0,self.num_functions-1)
        req = FuncRequest(rpc_id,f_type)
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
