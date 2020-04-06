#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from .end_measure import EndOfMeasurements
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.store import Store
from .dispatch_policies import RandomDispatchPolicy,JBSQDispatchPolicy

# Python base package includes
from random import randint

## A class which serves as a load balancer of incoming objects to a set of
## queues passed to it.
## Various queueing policies are implementable by extending the DispatchPolicy subclass, which takes a concurrency policy
## and overrides the "selectQueue" function.
class LoadBalancer(object):
    def __init__(self,simpy_env,lgen_to_interrupt,in_queue,disp_queues,dp=None):
        self.env = simpy_env
        self.in_q = in_queue
        self.worker_qs = disp_queues
        self.lgen_to_interrupt = lgen_to_interrupt
        self.killed = False
        if dp is None:
            self.dispatch_policy = RandomDispatchPolicy(len(disp_queues))
        else:
            self.dispatch_policy = dp
        self.action = self.env.process(self.run())

    def endSimGraceful(self):
        try:
            self.lgen_to_interrupt.action.interrupt("end of sim")
            if len(self.in_q.items) != 0:
                print("WARNING: Balancer got EoM packet from Load Generator, but there are still",len(self.in_q.items),"Reqs in the queue. Recommend check results.")
        except RuntimeError as e:
            print('Caught exception',e,'lets transparently ignore it')
        self.killed = True

    def selectQueue(self,req):
        the_q_num = self.dispatch_policy.select(req)
        return the_q_num, self.worker_qs[the_q_num]

    def run(self):
        while self.killed is False:
            if isinstance(self.dispatch_policy,JBSQDispatchPolicy):
                pass
                # TODO Peek at the queues until we can actually dispatch

            # Get next request from load generator
            req = yield self.in_q.get()
            if isinstance(req,EndOfMeasurements):
                self.endSimGraceful()
                continue

            # Dispatch it
            req.dispatch_time = self.env.now
            queue_num,the_queue = self.selectQueue(req)
            yield the_queue.put(req)
