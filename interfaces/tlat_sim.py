# Basic lame-o queueing simulation for M/M/K and single-cache block RPC.

import numpy as np
import pandas as pd
import scipy.stats as stats
import argparse
from scipy.special import binom as BinomCoefficient
from .LatencyTracker import ExactLatencyTracker

# Relative path required to have ./p3 and ./my_simpy in same dir
import sys
sys.path.append("..")
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.resource import FiniteQueueResource

ThroughputBytesPerSecond = 128e9 # full duplex
BytesPerPacket = 64
PacketInterarrival = 1/(ThroughputBytesPerSecond/BytesPerPacket)
Pck_ns = PacketInterarrival*(1e9)

Lambda_per_ns = 1000/(Pck_ns)

# Functions for service time/stats
TotalAccesses = 8
FirstLevelRolls = 3
CompulsoryMemAccesses = 8 - FirstLevelRolls
Prob_L1Hit = 0.8

tL1 = 2
tMem = 50

DEF_SERV_TIME = 1000
RTT = 5000 # 5 us
PRINT_INTERVAL = 500000

# Print out average and tail latency
def printServiceTimes(latStore):
    print("Average (median) is:",latStore.get_value_at_percentile(50))
    print("95th is:",latStore.get_value_at_percentile(95))
    print("99th is:",latStore.get_value_at_percentile(99))
    print("99.9th is:",latStore.get_value_at_percentile(99.9))

def RandomVarForServTime():
    numHits = stats.binom.rvs(FirstLevelRolls,Prob_L1Hit)
    coeff = BinomCoefficient(FirstLevelRolls,numHits)
    return coeff # TODO: Fixme

def serviceTimeGivenCacheHits(numHits):
    return (tL1 * numHits) + (tMem * ((FirstLevelRolls-numHits) + CompulsoryMemAccesses))

class RPCFactory(object):
    def __init__(self,ClassType,*args):
        self.ClassToConstruct = ClassType
        self.args = args

    def construct(self):
        return self.ClassToConstruct(*self.args)

class RPC(object):
    def __init__(self,env,distribution,theirNAMES,latencyTracker,rid):
        # every time you make one of these, run it.
        self.statsDist = distribution
        self.NAMES = theirNAMES
        self.env = env
        self.latencyTracker = latencyTracker
        self.name = "General Binomial Dist RPC"
        self.rid = rid

    def run(self):
        comp = False
        # record start time
        before_queue = self.env.now
        current_time = before_queue
        SLO = 10*self.getServiceTimeValue()
        Deadline = self.env.now + SLO

        while current_time < Deadline and not comp:
            #print("rpc",self.rid,"trying to request access, at time:",current_time)
            # queue waiting to get a core for service
            with self.NAMES.request() as req:
                try:
                    yield req
                    # GOT their names, now can serve
                    #print("rpc",self.rid,"GOT access, at time:",current_time)
                    yield self.env.timeout(self.getServiceTimeValue())
                    total_time = self.env.now - before_queue
                    self.latencyTracker.record_value(total_time)
                    #print("RPC",self.rid,"Finished @ time:",self.env.now)
                    comp = True
                except Interrupt as exc:
                    if exc.cause != 'maxQDepthExceeded':
                        raise ValueError('Unknown interrupt type')
                    else:
                        #print("RPC",self.rid,"overflowed the queue @ time:",self.env.now)
                        yield self.env.timeout(RTT)
                        current_time = self.env.now

        if not comp:
            #print("RPC",self.rid,"never finished by SLO deadline. Supposed to start at:",before_queue)
            self.latencyTracker.record_value(SLO)

class PointQuery(RPC):
    def __init__(self,env,dist,theirNAMES,latencyTracker,rid):
        super().__init__(env,dist,theirNAMES,latencyTracker,rid)
        self.name = "Point Query RPC"
        self.baseServiceTime = DEF_SERV_TIME
        self.action = env.process(self.run())

    def getServiceTimeValue(self):
        return self.baseServiceTime
        #cacheHits = self.statsDist.rvs(FirstLevelRolls,Prob_L1Hit)
        #return self.baseServiceTime - ( (tMem - tL1)*cacheHits )

class InlineScanQuery(RPC):
    def __init__(self,env,dist,theirNAMES,latencyTracker,rid):
        super().__init__(env,dist,theirNAMES,latencyTracker,rid)
        self.name = "Inline Scan Query RPC"
        self.baseServiceTime = 2500
        self.action = env.process(self.run())

    def getServiceTimeValue(self):
        return self.baseServiceTime

class NonInlineScanQuery(RPC):
    def __init__(self,env,dist,theirNAMES,latencyTracker,rid):
        super().__init__(env,dist,theirNAMES,latencyTracker,rid)
        self.name = "Non-inline Scan Query RPC"
        self.baseServiceTime = 10400
        self.action = env.process(self.run())

    def getServiceTimeValue(self):
        return self.baseServiceTime

class Server(FiniteQueueResource):
    def __init__(self,env,numIndepServers,qdepth):
        super().__init__(env,numIndepServers,qdepth)
        self.myCores = numIndepServers

class RPCGenerator(object):
    def __init__(self,env,ArrivalRate,theirNAMES,latStore,num,ppq,longtype):
        self.env = env
        self.server = theirNAMES
        self.myLambda = ArrivalRate
        self.latencyStore = latStore
        self.nRPCS = num
        self.percPointQueries = ppq
        self.longQueryClassType = longtype
        self.action = env.process(self.run())
        self.numSimulated = 0

    def run(self):
        while self.nRPCS > 0:
            if (self.nRPCS % PRINT_INTERVAL) == 0:
                print('RPCs simulated:',self.numSimulated)
                printServiceTimes(self.latencyStore)
            yield self.env.timeout(stats.expon.rvs(self.myLambda))
            #print("Generated new RPC at:",self.env.now)
            # binom generate for % of short queries
            boolForShortQuery = stats.binom.rvs(1,self.percPointQueries)
            if boolForShortQuery == 1:
                myRPC = RPCFactory(PointQuery,self.env,stats.binom,self.server,self.latencyStore,self.numSimulated).construct()
            else:
                myRPC = RPCFactory(NonInlineScanQuery,self.env,stats.binom,self.server,self.latencyStore,self.numSimulated).construct()

            self.nRPCS -= 1
            self.numSimulated += 1

def simulate(argsFromInvoker):
    parser = argparse.ArgumentParser(description='Run a M/M/k/N queueing sim.')
    parser.add_argument('-k','--NumberOfCores', dest='NumberOfCores', type=int, default=1,help='Number of servers to assume in the simulation (k in Kendall\'s notation)')
    parser.add_argument('-l','--Lambda', dest='LambdaArrivalRate', type=float, default=1,help='Lambda arrival rate of the simulation')
    parser.add_argument('-N', '--NumSlots', dest='NumQueueSlots', type=int, default=1,help='Max number of slots in the shared queue.')
    parser.add_argument('-n', '--N_rpcs', dest='NumRPCs', type=int, default=1,help='Number of RPCS/messages/jobs to simulate.')
    parser.add_argument('-f', '--frac_short',dest='FractionShortRPCs', type=float, default=1.0,help='Fraction of RPCs that will be considered "short".')

    args = parser.parse_args(argsFromInvoker)
    print('Simulating nCores = {}, Lambda = {}, QueueDepth = {}, and NRPCS = {}'.format(args.NumberOfCores,args.LambdaArrivalRate,args.NumQueueSlots,args.NumRPCs))

    env = Environment()
    # all measurements in range: [STime, 1000*STime], with a precision of 3 digits
    #latencyStore = HdrHistogram(DEF_SERV_TIME-10 , DEF_SERV_TIME*1000, 5)
    latencyStore = ExactLatencyTracker()
    theirNAMES = Server(env,args.NumberOfCores,args.NumQueueSlots)
    # pass number of events to the generator
    poissonGen = RPCGenerator(env,args.LambdaArrivalRate,theirNAMES,latencyStore,args.NumRPCs,args.FractionShortRPCs,NonInlineScanQuery)
    env.run()
    printServiceTimes(latencyStore)
