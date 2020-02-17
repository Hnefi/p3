#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
from .end_measure import EndOfMeasurements
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.store import Store

## A class which serves as a load balancer of incoming objects to a set of
## queues passed to it.
## Various queueing policies are implementable by extending the class
class LoadBalancerBase(object):
    def __init__(self,simpy_env,lgen_to_interrupt,in_queue,disp_queues):
        self.env = simpy_env
        self.in_q = in_queue
        self.worker_qs = disp_queues
        self.lgen_to_interrupt = lgen_to_interrupt
        self.killed = False
        self.action = self.env.process(self.run())

    def endSimGraceful(self):
        try:
            self.lgen_to_interrupt.action.interrupt("end of sim")
            if len(self.in_q.items) != 0:
                print("WARNING: Balancer got EoM packet from Load Generator, but there are still",len(self.in_q.items),"Reqs in the queue. Recommend check results.")
        except RuntimeError as e:
            print('Caught exception',e,'lets transparently ignore it')
        self.killed = True

    def run(self):
        while self.killed is False:
            # Start new RPC
            req = yield self.in_q.get()
            if isinstance(req,EndOfMeasurements):
                self.endSimGraceful()
                continue
