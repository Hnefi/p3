# Basic lame-o queueing simulation for M/M/K and single-cache block RPC.

import numpy as np
import pandas as pd
import scipy.stats as stats
import argparse
from scipy.special import binom as BinomCoefficient
from .LatencyTracker import ExactLatencyTracker
from hdrh.histogram import HdrHistogram
from random import randint

# Relative path required to have ./p3 and ./my_simpy in same dir
import sys
sys.path.append("..")
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.resource import FiniteQueueResource, Resource

# Interval to print how many RPCs this generator has run
PRINT_INTERVAL = 100000

# some random DRAM parameters, can un-hardcode this later
tCAS = 14
tRP = 14
tRAS = 24
tOffchip = 25
RB_HIT_RATE = 100

# Print out average and tail latency
def printServiceTimes(latStore):
    print("Average (median) is:",latStore.get_value_at_percentile(50))
    print("95th is:",latStore.get_value_at_percentile(95))
    print("99th is:",latStore.get_value_at_percentile(99))
    print("99.9th is:",latStore.get_value_at_percentile(99.9))

def getServiceTimes(latStore):
    percentiles = [ 50, 95, 99, 99.9 ]
    vals = [ latStore.get_value_at_percentile(p) for p in percentiles ]
    return zip(percentiles,vals)

class RPCFactory(object):
    def __init__(self,ClassType,*args):
        self.ClassToConstruct = ClassType
        self.args = args

    def construct(self):
        return self.ClassToConstruct(*self.args)

class InfiniteQueueDRAM(Resource):
    def __init__(self,env,nbanks):
        super().__init__(env,nbanks)
        self.num_banks = nbanks

    def getBankLatency(self):
        r = randint(0,100)
        if r <= RB_HIT_RATE:
            return tOffchip + tCAS
        else:
            return tOffchip + tRP + tRAS + tCAS

class Server(FiniteQueueResource):
    def __init__(self,env,numIndepServers,qdepth):
        super().__init__(env,numIndepServers,qdepth)
        self.myCores = numIndepServers

class NIPacket(object):
    def __init__(self,env,resource_queues,ddio):
        self.env = env
        self.queues = resource_queues
        self.p_ddio = ddio
        self.action = env.process(self.run())

    def run(self):
        rand_ddiohit = randint(0,100)
        if rand_ddiohit <= self.p_ddio:
            return # no dram traffic

        # Else queue up for dram.
        q = self.queues[randint(0,len(self.queues)-1)]
        with q.request() as req:
            try:
                yield req
                yield self.env.timeout(q.getBankLatency())
            except Interrupt as e:
                raise e

class NI(object):
    def __init__(self,env,ArrivalRate,resource_queues,p_ddio):
        self.env = env
        self.queues = resource_queues
        self.myLambda = ArrivalRate
        self.prob_ddio = p_ddio
        self.action = env.process(self.run())

    def run(self):
        while True:
            try:
                yield self.env.timeout(self.myLambda)
                r = NIPacket(self.env,self.queues,self.prob_ddio)
            except Interrupt:
                return

class ClosedLoopRPCGenerator(object):
    def __init__(self,env,sharedQueues,latStore,num,stime,NIToInterrupt,i):
        self.env = env
        self.queues = sharedQueues
        self.latencyStore = latStore
        self.nRPCS = num
        self.numSimulated = 0
        self.ni_to_interrupt = NIToInterrupt
        self.rpcid = i
        self.serv_time = stime
        if i is 0:
            self.isMaster = True
        else:
            self.isMaster = False
        self.action = env.process(self.run())

    def run(self):
        while self.nRPCS > 0:
            if (self.nRPCS % PRINT_INTERVAL) == 0:
                print('RPCs simulated:',self.numSimulated)

            # Start new RPC
            before_queue = self.env.now
            q = self.queues[randint(0,len(self.queues)-1)] # Pick a queue
            # Mem. request 1
            with q.request() as req:
                yield req
                r = q.getBankLatency()
                #print('Core num',self.rpcid,', RPC num',self.numSimulated,'doing mem req. 1, should wait for',r)
                yield self.env.timeout(r)

            yield self.env.timeout(self.serv_time)

            q = self.queues[randint(0,len(self.queues)-1)] # Pick another queue
            # Mem. request 2
            with q.request() as req:
                yield req
                r = q.getBankLatency()
                #print('Core num',self.rpcid,', RPC num',self.numSimulated,'doing mem req. 2, should wait for',r)
                yield self.env.timeout(r)
            total_time = self.env.now - before_queue
            #print('Core num',self.rpcid,', RPC num',self.numSimulated,'total processing time',total_time)
            self.latencyStore.record_value(total_time)
            self.nRPCS -= 1
            self.numSimulated += 1

        # Terminate sim, kill the NI
        if self.isMaster is True:
            self.ni_to_interrupt.action.interrupt()

def simulateAppAndNI_DRAM(argsFromInvoker):
    parser = argparse.ArgumentParser(description='Run a M*k/D/k/N queueing sim.')
    parser.add_argument('-k','--NumberOfChannels', dest='NumberOfChannels', type=int, default=1,help='Number of DRAM chs. to assume in the simulation (k in Kendall\'s notation)')
    parser.add_argument('-c','--NumberOfCores', dest='NumberOfCores', type=int, default=1,help='Number of application cores executing RPCs.')
    parser.add_argument('-l','--LambdaArrivalRate', dest='LambdaArrivalRate', type=float, default=1,help='Lambda arrival rate of the simulation')
    parser.add_argument('-B','--Bandwidth', dest='BWGbps', type=float, default=40,help='NI BW in Gbps')
    parser.add_argument('-b','--BanksPerChannel', dest='BanksPerChannel', type=int, default=1,help='DRAM banks per channel')
    parser.add_argument('-N', '--NumSlots', dest='NumQueueSlots', type=int, default=-1,help='Max number of slots in each queue (-1 if unlimited).')
    parser.add_argument('-n', '--N_rpcs', dest='NumRPCs', type=int, default=1,help='Number of RPCS/messages/jobs to simulate.')
    parser.add_argument('-s', '--serv_time', dest='serv_time', type=int, default=100,help='Service time of the RPC')
    parser.add_argument('-S', '--Servers', dest='servers', type=int, default=10000,help='Number of server nodes to assume.')
    args = parser.parse_args(argsFromInvoker.split(' '))
    env = Environment()


    # 100ns to 100us, with a precision of 0.1%
    latencyStore = HdrHistogram(100, 100000, 3)

    # Number of connections per server
    #N_threads = args.servers * args.NumberOfCores
    N_connections = args.servers * args.servers
    # Buffer space compared to LLC size
    BDP = float(args.BWGbps)/8.0 * 1000 # Gbps/8 * ns = bytes
    BufSpace = N_connections * BDP
    LLCSpace = 1.5e6*args.NumberOfCores # 1.5MB/core, Xeon Scalable

    # Prob NI does DDIO into cache
    p_ddio = (float(LLCSpace) / BufSpace)*100
    #print('p_hit',p_ddio)

    print('[NEW JOB: BW',args.BWGbps,', lambda',args.LambdaArrivalRate,'BDP',BDP,'Buffer space(MB)',BufSpace/1e6,', LLC Size(MB)',LLCSpace/1e6,'Prob DDIO hit',p_ddio,']')

    # Create N queues, one per DRAM channel
    if args.NumQueueSlots == -1:
        DRAMChannels = [InfiniteQueueDRAM(env,args.BanksPerChannel) for i in range(args.NumberOfChannels)]
    else:
        DRAMChannels = [Server(env,args.BanksPerChannel,args.NumQueueSlots) for i in range(args.NumberOfChannels)]

    # NI antagonist
    NIDevice = NI(env,args.LambdaArrivalRate,DRAMChannels,p_ddio)
    # create rpc generator
    CPUsModel = [ClosedLoopRPCGenerator(env,DRAMChannels,latencyStore,(args.NumRPCs/args.NumberOfCores),args.serv_time,NIDevice,i) for i in range(args.NumberOfCores)]

    env.run()
    return [ getServiceTimes(latencyStore), 0 ]
