#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020
from .serv_times.exp_generator import ExpServTimeGenerator
from .serv_times.userv_function import DynamicUServTime

class AbstractCore(object):
    def __init__(self,core_id,lgen_to_interrupt):
        # Used for calculating service stability
        self.lgen_to_interrupt = lgen_to_interrupt
        self.kill_sim_threshold = 100000
        self.lastFiveSTimes = [ ]
        if core_id == 0:
            self.isMaster = True
        else:
            self.isMaster = False

    def putSTime(self,time):
        self.lastFiveSTimes.append(time)
        if len(self.lastFiveSTimes) >= 5:
            del self.lastFiveSTimes[0]

    def checkTimeOverThreshold(self,item):
        if item >= self.kill_sim_threshold:
            return True
        return False

    def isSimulationUnstable(self):
        timeGreaterThanThresholdList = [ self.checkTimeOverThreshold(x) for x in self.lastFiveSTimes ]
        if all(timeGreaterThanThresholdList) is True:
            return True
        return False

    def endSimUnstable(self):
        if self.isMaster is True:
            try:
                self.lgen_to_interrupt.action.interrupt("unstable")
            except RuntimeError as e:
                print('Caught exception',e,'lets transparently ignore it')
        self.killed = True

class uServCore(AbstractCore):
    def __init__(self,simpy_env,core_id,request_queue,measurement_store,stime_gen,lgen_to_interrupt):
        super().__init__(core_id,lgen_to_interrupt)
        self.env = simpy_env
        self.id = core_id
        self.in_q = request_queue
        self.latency_store = measurement_store
        self.stime_gen = stime_gen
        self.killed = False
        self.action = self.env.process(self.run())
        self.numSimulated = 0

    def run(self):
        while self.killed is False:
            rpc = yield self.in_q.get()

            rpcNumber = rpc.num
            rpc.start_proc_time = self.env.now

            # Model a service time
            yield self.env.timeout(self.stime_gen.get())

            # RPC is done
            rpc.end_proc_time = self.env.now
            rpc.completion_time = self.env.now # This may need to be changed to model any "end of rpc" actions
            total_time = rpc.getTotalServiceTime()
            self.latency_store.record_value(total_time)
            self.putSTime(total_time)

            if self.isMaster is True and self.isSimulationUnstable() is True:
                print('Simulation was unstable, last five service times from core 0 were:',self.lastFiveSTimes,', killing sim.')
                self.endSimUnstable()
            self.numSimulated += 1

class DynamicUServCore(AbstractCore):
    def __init__(self,simpy_env,core_id,request_queue,measurement_store,lgen_to_interrupt,WorkingSet,FuncGrouping,funcs_per_btb,library_fraction):
        super().__init__(core_id,lgen_to_interrupt)
        self.env = simpy_env
        self.id = core_id
        self.in_q = request_queue
        self.latency_store = measurement_store
        # Import service time generator
        from .serv_times.userv_function import DynamicUServTime

        self.stime_gen = DynamicUServTime(workset=WorkingSet,num_functions=FuncGrouping,
                                       func_thrashing_boundary=funcs_per_btb,library_fraction=library_fraction)
        self.killed = False
        self.action = self.env.process(self.run())
        self.numSimulated = 0

    def run(self):
        while self.killed is False:
            rpc = yield self.in_q.get()

            rpcNumber = rpc.num
            rpc.start_proc_time = self.env.now

            # Model a service time
            yield self.env.timeout(self.stime_gen.get(rpc.getFuncType()))

            # RPC is done
            rpc.end_proc_time = self.env.now
            rpc.completion_time = self.env.now # This may need to be changed to model any "end of rpc" actions
            total_time = rpc.getTotalServiceTime()
            self.latency_store.record_value(total_time)
            self.putSTime(total_time)

            if self.isMaster is True and self.isSimulationUnstable() is True:
                print('Simulation was unstable, last five service times from core 0 were:',self.lastFiveSTimes,', killing sim.')
                self.endSimUnstable()
            self.numSimulated += 1


class RPCCore(AbstractCore):
    def __init__(self,simpy_env,core_id,request_queue,measurement_store,rd_gen,wr_gen,lgen_to_interrupt):
        super().__init__(core_id,lgen_to_interrupt)
        self.env = simpy_env
        self.id = core_id
        self.in_q = request_queue
        self.latency_store = measurement_store
        self.read_distribution_generator = rd_gen
        self.write_distribution_generator = wr_gen
        self.killed = False
        self.action = self.env.process(self.run())
        self.numSimulated = 0

    def run(self):
        while self.killed is False:
            rpc = yield self.in_q.get()

            rpcNumber = rpc.num
            rpc.start_proc_time = self.env.now

            # Model a service time
            if rpc.getWrite():
                yield self.env.timeout(self.write_distribution_generator.get())
            else:
                yield self.env.timeout(self.read_distribution_generator.get())

            # RPC is done
            rpc.end_proc_time = self.env.now
            rpc.completion_time = self.env.now # This may need to be changed to model any "end of rpc" actions
            total_time = rpc.getTotalServiceTime()
            self.latency_store.record_value(total_time)
            self.putSTime(total_time)

            if self.isMaster is True and self.isSimulationUnstable() is True:
                print('Simulation was unstable, last five service times from core 0 were:',self.lastFiveSTimes,', killing sim.')
                self.endSimUnstable()
            self.numSimulated += 1
