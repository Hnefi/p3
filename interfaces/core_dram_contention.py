# Basic lame-o queueing simulation for M/M/K and single-cache block RPC.

import numpy as np
import pandas as pd
import scipy.stats as stats
import argparse
from scipy.special import binom as BinomCoefficient
from .LatencyTracker import ExactLatencyTracker
from hdrh.histogram import HdrHistogram
from random import randint
from math import floor

# Relative path required to have ./p3 and ./my_simpy in same dir
import sys
sys.path.append("..")
from my_simpy.src.simpy import Environment,Interrupt
from my_simpy.src.simpy.resources.resource import FiniteQueueResource, Resource
from my_simpy.src.simpy.resources.store import Store

# Interval to print how many RPCs this generator has run
PRINT_INTERVAL = 100000

# some random DRAM parameters, can un-hardcode this later
tCAS = 14
tRP = 14
tRAS = 24
tOffchip = 25
RB_HIT_RATE = 75

# Min serv. time (ns)
MIN_STIME_NS = 100
MAX_STIME_NS = 1000 * MIN_STIME_NS

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

class RPC(object):
    def __init__(self,d,llc_hit):
        self.dispatch_time = d
        self.start_proc_time = -1
        self.end_proc_time = -1
        self.completion_time = -1
        self.hit = llc_hit

    def getQueuedTime(self):
        return self.start_proc_time - self.dispatch_time

    def getProcessingTime(self):
        return self.end_proc_time - self.start_proc_time

    def getTotalServiceTime(self):
        return self.completion_time - self.dispatch_time

class BWBucket(object):
    def __init__(self,start,end):
        self.start_time = start
        self.end_time = end
        self.bytesTransferred = 0

    def addReq(self,sz):
        self.bytesTransferred += sz

    def asTuple(self):
        return (self.start_time,self.end_time,self.bytesTransferred)

    def getIntervalBW(self):
        return self.bytesTransferred / float(self.end_time - self.start_time) # GB/s

class BWProfiler(object):
    def __init__(self,e,nbanks,bucketInterval):
        self.env = e
        self.nbanks = nbanks
        self.interval = bucketInterval
        self.buckets = [ ]
        self.currentBucket = BWBucket(self.env.now,self.env.now + self.interval)

    def completeReq(self,t,sz):
        if t > self.currentBucket.end_time:
            self.buckets.append(self.currentBucket) # finished this one, make new
            nextStartTime = self.currentBucket.end_time
            self.currentBucket = BWBucket(nextStartTime,nextStartTime + self.interval)
            #print('making new BW bucket with range [',nextStartTime,',',nextStartTime + self.interval,']')
        #print('completing DRAM req of size',sz,'at time',t)
        self.currentBucket.addReq(sz)

    def getBucketBWs(self):
        self.buckets.append(self.currentBucket) # terminate current bucket
        return [ i.getIntervalBW() for i in self.buckets ]

class InfiniteQueueDRAM(Resource):
    def __init__(self,env,nbanks):
        super().__init__(env,nbanks)
        self.num_banks = nbanks
        self.env = env

        INTERVAL = 10000 # 10 us
        self.profiler = BWProfiler(env,nbanks,INTERVAL)

    def getIntervalBandwidths(self):
        return self.profiler.getBucketBWs()

    def getBankLatency(self):
        r = randint(0,100)
        if r <= RB_HIT_RATE:
            return tOffchip + tCAS
        else:
            return tOffchip + tRP + tRAS + tCAS

    def completeReq(self,sz):
        self.profiler.completeReq(self.env.now,sz)

class Server(FiniteQueueResource):
    def __init__(self,env,numIndepServers,qdepth):
        super().__init__(env,numIndepServers,qdepth)
        self.myCores = numIndepServers

# This needs to be a seperate process to run independently to arrivals
class RPCDispatch(object):
    def __init__(self,env,resource_queues,dq,ddio,sz,i):
        self.env = env
        self.queues = resource_queues
        self.dispatch_queue = dq
        self.p_ddio = ddio
        self.RPCSize = sz
        self.num = i
        self.action = env.process(self.run())

    def rollHit(self):
        rand_ddiohit = randint(0,100)
        if rand_ddiohit <= self.p_ddio:
            return True
        return False

    def run(self):
        ddio_hit = self.rollHit()
        newRPC = RPC(self.env.now,ddio_hit)
        num_reqs = floor(self.RPCSize / 64)
        if ddio_hit is True:
            for i in range(num_reqs):
                yield self.env.timeout(1)
            #print('HIT: NI dispatched rpc num',i,'at time',self.env.now)
            yield self.dispatch_queue.put(newRPC)
        else:
            for i in range(num_reqs):
                # Queue up for DRAM
                q = self.queues[randint(0,len(self.queues)-1)]
                with q.request() as req:
                    try:
                        yield req
                        yield self.env.timeout(q.getBankLatency())
                    except Interrupt as e:
                        raise e
                q.completeReq(64)
            yield self.dispatch_queue.put(newRPC)
            #print('MISS: NI dispatched rpc num',i,'at time',self.env.now)

class NI(object):
    def __init__(self,env,ArrivalRate,resource_queues,p_ddio,RPCSize,dispatch_queue,N):
        self.env = env
        self.queues = resource_queues
        self.myLambda = ArrivalRate
        self.prob_ddio = p_ddio
        self.dispatch_queue = dispatch_queue
        self.RPCSize = RPCSize
        self.numRPCs = N
        self.action = env.process(self.run())

    def run(self):
        numSimulated = 0
        while numSimulated < self.numRPCs:
            try:
                # TODO: does this need to change if we unroll
                #       multiple DRAM reqs and overshoot the lambda?
                yield self.env.timeout(self.myLambda)
                r = RPCDispatch(self.env,self.queues,self.dispatch_queue,self.prob_ddio,self.RPCSize,numSimulated)
                numSimulated += 1
            except Interrupt as i:
                print("NI killed with Simpy exception:",i,"....EoSim")
                return

class ClosedLoopRPCGenerator(object):
    def __init__(self,env,sharedQueues,latStore,stime,NIToInterrupt,i,max_stime_ns,dispatch_queue,p_ddio,sz):
        self.env = env
        self.queues = sharedQueues
        self.latencyStore = latStore
        self.numSimulated = 0
        self.ni_to_interrupt = NIToInterrupt
        self.cid = i
        self.serv_time = stime
        self.kill_sim_threshold = max_stime_ns
        self.dispatch_queue = dispatch_queue
        self.p_hit = p_ddio
        self.RPCSize = sz
        self.killed = False
        self.lastFiveSTimes = [ ]
        if i is 0:
            self.isMaster = True
        else:
            self.isMaster = False
        self.action = env.process(self.run())

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

    def endSim(self):
        if self.isMaster is True:
            try:
                self.ni_to_interrupt.action.interrupt()
            except RuntimeError as e:
                print('Caught exception',e,'lets transparently ignore it')
        self.killed = True

    # read or write rpc buffer
    def doRPCBufferInteraction(self,hit):
        num_reqs = floor(self.RPCSize / 64)
        if hit is True:
            for i in range(num_reqs):
                yield self.env.timeout(1)
        else:
            for i in range(num_reqs):
                q = self.queues[randint(0,len(self.queues)-1)] # Pick a queue
                with q.request() as req:
                    yield req
                    r = q.getBankLatency()
                    yield self.env.timeout(r)
                q.completeReq(64)

    def run(self):
        while self.killed is False:
            # Start new RPC
            rpc = yield self.dispatch_queue.get()
            #print('core',self.cid,'got rpc from the dispatch queue',rpc,'at time',self.env.now,'dispatch time',rpc.dispatch_time)
            rpc.start_proc_time = self.env.now
            self.doRPCBufferInteraction(rpc.hit)
            #print('RPC buffer interaction [hit?',rpc.hit,']')

            # Mem. request 1
            q = self.queues[randint(0,len(self.queues)-1)]
            with q.request() as req:
                yield req
                r = q.getBankLatency()
                yield self.env.timeout(r)
            q.completeReq(64)

            yield self.env.timeout(self.serv_time)

            # Mem. request 2
            q = self.queues[randint(0,len(self.queues)-1)]
            with q.request() as req:
                yield req
                r = q.getBankLatency()
                #print('Core num',self.rpcid,', RPC num',self.numSimulated,'doing mem req. 2, should wait for',r)
                yield self.env.timeout(r)
            q.completeReq(64)

            rpc.end_proc_time = self.env.now

            # Put RPC response to memory
            self.doRPCBufferInteraction(rpc.hit)
            #print('RPC buffer interaction [hit?',rpc.hit,']')

            rpc.completion_time = self.env.now
            total_time = rpc.getTotalServiceTime()
            #print('Core num',self.cid,', RPC num',self.numSimulated,'total processing time',total_time)
            self.latencyStore.record_value(total_time)
            self.putSTime(total_time)
            if self.isMaster is True and self.isSimulationUnstable() is True:
                print('Simulation was unstable, last five service times from core 0 were:',self.lastFiveSTimes,', killing sim.')
                self.endSim()

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

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
    parser.add_argument('-R', '--SingleBuffer', dest='singleBuffer', type=str2bool,default=False,const=True,nargs='?',help='Whether or not to assume a single buffer.')
    parser.add_argument('--printDRAMBW', dest='printDRAMBW', type=str2bool,default=False,const=True,nargs='?',help='Whether or not to print DRAM BW characteristics post-run.')

    args = parser.parse_args(argsFromInvoker.split(' '))
    env = Environment()

    RPC_SIZE= 64 # TODO: make dynamic

    dram_avg_lat = tOffchip + (RB_HIT_RATE/100)*tCAS + (1-(RB_HIT_RATE/100))*(tRP+tRAS+tCAS)
    #print('Avg DRAM lat:',dram_avg_lat)
    #print('Naive DRAM estimate BW:',64/dram_avg_lat * 8)

    # 100ns to 100us, with a precision of 0.1%
    latencyStore = HdrHistogram(MIN_STIME_NS, MAX_STIME_NS, 3)

    # Number of connections per server
    #N_threads = args.servers * args.NumberOfCores
    N_connections = args.servers * args.servers
    # Buffer space compared to LLC size
    BDP = float(args.BWGbps)/8.0 * 1000 # Gbps/8 * ns = bytes
    if args.singleBuffer is True:
        BufSpace = BDP
    else:
        BufSpace = N_connections * BDP
    LLCSpace = 1.5e6*args.NumberOfCores # 1.5MB/core, Xeon Scalable

    # Prob NI does DDIO into cache
    if BufSpace <= LLCSpace:
        p_ddio = 100
    else:
        p_ddio = (float(LLCSpace) / BufSpace)*100

    #print('[NEW JOB: BW',args.BWGbps,', lambda',args.LambdaArrivalRate,'BDP',BDP,'Buffer space(MB)',BufSpace/1e6,', LLC Size(MB)',LLCSpace/1e6,'Prob DDIO hit',p_ddio,']')

    # Create N queues, one per DRAM channel
    if args.NumQueueSlots == -1:
        DRAMChannels = [InfiniteQueueDRAM(env,args.BanksPerChannel) for i in range(args.NumberOfChannels)]
    else:
        DRAMChannels = [Server(env,args.BanksPerChannel,args.NumQueueSlots) for i in range(args.NumberOfChannels)]

    # Dispatch qeuue
    dispatch_queue = Store(env) # FIXME: infinite length -> drop

    # NI antagonist
    NIDevice = NI(env,args.LambdaArrivalRate,DRAMChannels,p_ddio,RPC_SIZE,dispatch_queue,args.NumRPCs)

    # create rpc generator
    CPUsModel = [ClosedLoopRPCGenerator(env,DRAMChannels,latencyStore,args.serv_time,NIDevice,i,MAX_STIME_NS,dispatch_queue,p_ddio,RPC_SIZE) for i in range(args.NumberOfCores)]

    env.run()

    # print dram BW
    if args.printDRAMBW is True:
        dramChannelBW_Lists = [ ch.getIntervalBandwidths() for ch in DRAMChannels ] # list of lists
        for ch in dramChannelBW_Lists:
            print(ch)

    return [ getServiceTimes(latencyStore), 0 ]
