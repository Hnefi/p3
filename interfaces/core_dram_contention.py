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
    def __init__(self,n,d,llc_hit):
        self.num = n
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

class EndOfMeasurements(object):
    pass

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

class SingleMemoryRequest(object):
    def __init__(self,env,resource_queues,eventToSucceed):
        self.env = env
        self.queues = resource_queues
        self.event = eventToSucceed
        self.action = env.process(self.run())

    # runs and then fulfills the event when it's done
    def run(self):
        #print('Single request starting at',self.env.now)
        q = self.queues[randint(0,len(self.queues)-1)]
        with q.request() as req:
            yield req
            yield self.env.timeout(q.getBankLatency())
        q.completeReq(64)
        # raise the event
        #print('Single request raising event at',self.env.now)
        self.event.succeed()

# Also a separate process to run independently to the above requester
class RPCDispatchRequest(object):
    def __init__(self,env,resource_queues,sz,eventCompletion,interRequestTime,dispatch_q,rnum,no_dispatch=False):
        self.env = env
        self.queues = resource_queues
        self.size = sz
        self.interRequestTime = interRequestTime
        self.eventCompletion = eventCompletion
        self.dispatch_queue = dispatch_q
        self.num = rnum
        self.no_dispatch = no_dispatch
        self.action = self.env.process(self.run())

    def run(self):
        num_reqs = floor(self.size / 64)
        eventArray = [ self.env.event() for i in range(num_reqs) ]
        for i in range(num_reqs):
            #print('RPC',self.num,'created new single req. at',self.env.now)
            SingleMemoryRequest(self.env,self.queues,eventArray[i])
            if i < (num_reqs-1):
                yield self.env.timeout(self.interRequestTime)

        # call to upper layer
        #print('RPC',self.num,'completed packet writes at',self.env.now)
        self.eventCompletion.succeed()

        if self.no_dispatch is False:
            # sleep until all events are fulfilled
            for i in range(num_reqs):
                yield eventArray[i]
                #print('RPC',self.num,'activating event at',self.env.now)
            newRPC = RPC(self.num,self.env.now,False) # ddio miss on writing payloads to dram
            yield self.dispatch_queue.put(newRPC)

class SyncOverlappedMemoryRequest(object):
    def __init__(self,env,resource_queues,sz,completionSignal,interRequestTime=1):
        self.env = env
        self.queues = resource_queues
        self.size = sz
        self.interRequestTime = interRequestTime
        self.completionSignal = completionSignal
        self.action = env.process(self.run())

    def run(self):
        num_reqs = floor(self.size / 64)
        eventArray = [ self.env.event() for i in range(num_reqs) ]
        for i in range(num_reqs):
            SingleMemoryRequest(self.env,self.queues,eventArray[i])
            if i < (num_reqs-1):
                yield self.env.timeout(self.interRequestTime)

        # sleep until all events are fulfilled
        for i in range(num_reqs):
            yield eventArray[i]

        self.completionSignal.succeed()

# Also a separate process to run independently to the above requester
class AsyncMemoryRequest(object):
    def __init__(self,env,resource_queues,sz,interRequestTime=1):
        self.env = env
        self.queues = resource_queues
        self.size = sz
        self.interRequestTime = interRequestTime
        self.action = env.process(self.run())

    def run(self):
        num_reqs = floor(self.size / 64)
        eventArray = [ self.env.event() for i in range(num_reqs) ]
        for i in range(num_reqs):
            #print('created new single req. at',self.env.now)
            SingleMemoryRequest(self.env,self.queues,eventArray[i])
            if i < (num_reqs-1):
                yield self.env.timeout(self.interRequestTime)

        # sleep until all events are fulfilled
        for i in range(num_reqs):
            #print('asyncmemreqest yielding/passivating at',self.env.now)
            yield eventArray[i]
            #print('asyncmemreqest activating at',self.env.now)

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

    def rollHit(self):
        rand_ddiohit = randint(0,100)
        if rand_ddiohit <= self.prob_ddio:
            return True
        return False

    def run(self):
        numSimulated = 0
        while numSimulated < self.numRPCs:
            try:
                ddio_hit = self.rollHit()
                if ddio_hit is True:
                    num_reqs = floor(self.RPCSize / 64)
                    for i in range(num_reqs):
                        if i < (num_reqs-1):
                            yield self.env.timeout(self.myLambda)
                    newRPC = RPC(numSimulated,self.env.now,ddio_hit)
                    #print('HIT: NI dispatched rpc num',numSimulated,'at time',self.env.now)
                    yield self.dispatch_queue.put(newRPC)
                else:
                    # Launch a multi-packet request to memory, dispatch when it is done.
                    payloadsDoneEvent = self.env.event()
                    payloadWrite = RPCDispatchRequest(self.env, self.queues, self.RPCSize, payloadsDoneEvent, self.myLambda,self.dispatch_queue,numSimulated)
                    yield payloadsDoneEvent # all payloads written

                yield self.env.timeout(self.myLambda)
                numSimulated += 1
            except Interrupt as i:
                print("NI killed with Simpy exception:",i,"....EoSim")
                return

        yield self.dispatch_queue.put(EndOfMeasurements())

        # After the dispatch is done, keep generating the traffic for realistic measurements.
        while True:
            try:
                ddio_hit = self.rollHit()
                if ddio_hit is True:
                    newRPC = RPC(-1,self.env.now,ddio_hit)
                    num_reqs = floor(self.RPCSize / 64)
                    for i in range(num_reqs):
                        if i < (num_reqs-1):
                            yield self.env.timeout(self.myLambda)
                else:
                    # Launch a multi-packet request to memory, dispatch when it is done.
                    payloadsDoneEvent = self.env.event()
                    payloadWrite = RPCDispatchRequest(self.env, self.queues, self.RPCSize, payloadsDoneEvent, self.myLambda,self.dispatch_queue,numSimulated,no_dispatch=True)
                    yield payloadsDoneEvent # all payloads written

                yield self.env.timeout(self.myLambda)
            except Interrupt as i:
                #print("NI killed in post-dispatch phase, exception:",i,"....End of Sim...")
                return

class ClosedLoopRPCGenerator(object):
    def __init__(self,env,sharedQueues,latStore,mean_service_time,NIToInterrupt,i,max_stime_ns,dispatch_queue,p_ddio,sz,num_mem_reqs,amat,micaPrefetch):
        self.env = env
        self.queues = sharedQueues
        self.latencyStore = latStore
        self.numSimulated = 0
        self.ni_to_interrupt = NIToInterrupt
        self.cid = i
        self.kill_sim_threshold = max_stime_ns
        self.dispatch_queue = dispatch_queue
        self.p_hit = p_ddio
        self.RPCSize = sz
        self.killed = False
        self.prefetch = micaPrefetch
        self.lastFiveSTimes = [ ]

        # Values used for calculating processing time, given
        # the number of memory requests
        self.num_mem_reqs = num_mem_reqs
        self.mean_serv_time = mean_service_time
        self.amat_to_assume = amat

        self.mean_cpu_time = self.mean_serv_time - (self.num_mem_reqs * self.amat_to_assume)
        self.mean_cpu_time_interval = float(self.mean_cpu_time) / (self.num_mem_reqs-1)
        assert self.mean_cpu_time_interval > 0, "Can't attain this total service time, num_mem_reqs * DRAM amat is >= the CPU time."
        self.serv_time_dist = stats.expon(scale = self.mean_cpu_time_interval)
        assert self.serv_time_dist.mean() == self.mean_cpu_time_interval, "Setup the distribution wrongly. Mean:"+str(self.serv_time_dist.mean())+", interval: "+str(self.mean_cpu_time_interval)

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

    def endSimGraceful(self):
        try:
            self.ni_to_interrupt.action.interrupt("end of sim")
            if len(self.dispatch_queue.items) != 0:
                print("WARNING: Core got EoM packet from NI, but there are still",len(self.dispatch_queue.items),"RPCs in the queue. Recommend check results.")
        except RuntimeError as e:
            print('Caught exception',e,'lets transparently ignore it')
        self.killed = True

    def endSimUnstable(self):
        if self.isMaster is True:
            try:
                self.ni_to_interrupt.action.interrupt("unstable")
            except RuntimeError as e:
                print('Caught exception',e,'lets transparently ignore it')
        self.killed = True

    def run(self):
        while self.killed is False:
            # Start new RPC
            rpc = yield self.dispatch_queue.get()
            if isinstance(rpc,EndOfMeasurements):
                #print('End of simulation received by core',self.cid,', interrupting NI')
                self.endSimGraceful()
                continue

            rpcNumber = rpc.num
            #print('core',self.cid,'got rpc #',rpcNumber,'from the dispatch queue at time',self.env.now,'dispatch time',rpc.dispatch_time)
            rpc.start_proc_time = self.env.now

            # model buffer reads
            num_reqs = floor(self.RPCSize / 64)
            if rpc.hit is True:
                for i in range(num_reqs):
                    yield self.env.timeout(1)
            else:
                buffersReadEvent = self.env.event()
                #print('rpc went to sleep at time',self.env.now)
                physBufferReader = SyncOverlappedMemoryRequest(self.env,self.queues,self.RPCSize,buffersReadEvent)
                yield buffersReadEvent # wait for all requests to return
                #print('Re-woke up rpc at time',self.env.now)

            #do prefetch for next rpc packet
            if self.prefetch is True:
                pf = AsyncMemoryRequest(self.env, self.queues, self.RPCSize)

            # Enter processing loop
            for i in range(self.num_mem_reqs):
                # Do req. to random MC
                q = self.queues[randint(0,len(self.queues)-1)]
                with q.request() as req:
                    yield req
                    r = q.getBankLatency()
                    yield self.env.timeout(r)
                q.completeReq(64)

                #do prefetch for next metadata
                if self.prefetch is True:
                    pf = AsyncMemoryRequest(self.env, self.queues, self.RPCSize)

                # spend some Cpu time, calculated in __init__
                if i < (self.num_mem_reqs-1): # don't do processing the last time
                    yield self.env.timeout(self.mean_cpu_time_interval)

            # RPC is done
            rpc.end_proc_time = self.env.now

            # Put RPC response to memory
            num_reqs = floor(self.RPCSize / 64)
            if rpc.hit is True:
                for i in range(num_reqs):
                    yield self.env.timeout(1)
            else:
                buffersReadEvent = self.env.event()
                physBufferReader = SyncOverlappedMemoryRequest(self.env,self.queues,self.RPCSize,buffersReadEvent)
                yield buffersReadEvent # wait for all requests to return

            rpc.completion_time = self.env.now
            total_time = rpc.getTotalServiceTime()
            #print('Core num',self.cid,', RPC num',rpcNumber,'total processing time',rpc.getProcessingTime(),', total e-e service time',total_time)
            self.latencyStore.record_value(total_time)
            self.putSTime(total_time)
            if self.isMaster is True and self.isSimulationUnstable() is True:
                print('Simulation was unstable, last five service times from core 0 were:',self.lastFiveSTimes,', killing sim.')
                self.endSimUnstable()
            self.numSimulated += 1

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
    parser.add_argument('--reqsPerRPC', dest='numMemRequests', type=int, default=2,help='Number of memory requests to do per RPC.')
    parser.add_argument('--rpcSizeBytes', dest='rpcSizeBytes', type=int, default=64,help='Number of bytes making up each RPC\'s argument/return buffer.')
    parser.add_argument('-R', '--SingleBuffer', dest='singleBuffer', type=str2bool,default=False,const=True,nargs='?',help='Whether or not to assume a single buffer.')
    parser.add_argument('--printDRAMBW', dest='printDRAMBW', type=str2bool,default=False,const=True,nargs='?',help='Whether or not to print DRAM BW characteristics post-run.')
    parser.add_argument('--micaPrefetch', dest='micaPrefetch', type=str2bool,default=False,const=True,nargs='?',help='Whether or not to model MICA prefetching (roughly doubles BW utilization).')

    args = parser.parse_args(argsFromInvoker.split(' '))
    env = Environment()

    RPC_SIZE = args.rpcSizeBytes

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

    print('[NEW JOB: BW',args.BWGbps,', lambda',args.LambdaArrivalRate,'BDP',BDP,'Buffer space(MB)',BufSpace/1e6,', LLC Size(MB)',LLCSpace/1e6,'Prob DDIO hit',p_ddio,']')

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
    CPUsModel = [ClosedLoopRPCGenerator(env,DRAMChannels,latencyStore,args.serv_time,NIDevice,i,MAX_STIME_NS,dispatch_queue,p_ddio,RPC_SIZE,args.numMemRequests,dram_avg_lat,args.micaPrefetch) for i in range(args.NumberOfCores)]

    env.run()

    # print dram BW
    #if args.printDRAMBW is True:
        #dramChannelBW_Lists = [ ch.getIntervalBandwidths() for ch in DRAMChannels ] # list of lists
        #for ch in dramChannelBW_Lists:
            #print(ch)

    dramChannelBW_Lists = [ ch.getIntervalBandwidths() for ch in DRAMChannels ] # list of lists
    def avgBW(l):
        return sum(l,0.0)/len(l)

    #retList = [ getServiceTimes(latencyStore), 0 ] + [ avgBW(ch) for ch in dramChannelBW_Lists ]
    perCh_averages = [ avgBW(ch) for ch in dramChannelBW_Lists ]
    if args.printDRAMBW is True:
        print('DRAM channel bandwidths for job (',args.BWGbps,'):',perCh_averages)
    retList = [ getServiceTimes(latencyStore), 0, sum(perCh_averages) ]
    return retList
