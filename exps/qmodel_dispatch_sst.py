#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020

# my includes
from components.load_balancer import LoadBalancer
from components.nonuniform_loadgen import NonUniformUServLoadGen
from components.rpc_core import uServCore, DynamicUServCore
from components.serv_times.userv_function import StaticUServiceTime
from components.dispatch_policies.func_policies import SSTDispatch

# simpy includes
from my_simpy.src.simpy import Environment
from my_simpy.src.simpy.resources.store import Store

# python environment includes
import argparse
from hdrh.histogram import HdrHistogram
from math import floor

LIB_FRACTION=0.25

def run_exp(arg_string):
    parser = argparse.ArgumentParser(description='Basic simulation to compare affinity-based dispatch sizing.')
    parser.add_argument('-c','--NumWorkers', dest='NumWorkers', type=int, default=16,help='Number of worker cores in the queueing system. Default = 16')
    parser.add_argument('-a','--ArrivalRate',type=float,help="RPC inter-arrival time for the load gen (ns). Default = 1000",default=1000.0)
    parser.add_argument('--RequestsToSimulate',type=int,help="Number of requests to simulate for. Default = 1K",default = 1000)
    parser.add_argument('-G','--FunctionGrouping',type=int,help="Number of functions to assign to a core. Default = number of cores",default=0)
    parser.add_argument('-J','--CoreGrouping',type=int,help="Number of cores to assign to each function group. Default = 1",default=1)
    parser.add_argument('-N','--NumFunctions',type=int,help="Number of functions total. Default = 8",default=8)
    parser.add_argument('-W','--WorkingSetFile',type=str,help="File containing a pickled dictionary of function working sets.",default='func_wsets.p')
    parser.add_argument('-S','--CacheSize',type=int,help="Size of an L1 cache. Default = 64",default=64*1024)
    parser.add_argument('-L','--CoreLookahead',type=int,help="Cache block lookahead that the CPU can attain. Default = 1",default=1)
    parser.add_argument('--UseIdealSetup',action='store_true',help="Use ideal setup of single-queue w. best function runtime",default=False)
    parser.add_argument('--HistoryDepth',type=int,help="Depth of per-core RPC history stored by dispatcher. Default = 16",default=16)
    parser.add_argument('--LBThreshold',type=int,help="Threshold for dispatching to shortest queue. Default = 2",default=4)
    parser.add_argument('--UseAffinity',action='store_true',help="Use function-affinity based dispatch",default=False)
    parser.add_argument('--FuncPopularities',type=float,nargs='+',help="A list of floats representing the popularities of each function. Used for load generation. Must be equal to the number of functions.",required=True)
    args = parser.parse_args(arg_string.split())

    assert(args.UseAffinity) # This SST assumes we use a 100% affinity-based policy, to get shortest-possible service time

    # Set this to number of workers or explicitly specified values
    if args.FunctionGrouping == 0:
        FuncGrouping = args.NumWorkers
    else:
        FuncGrouping = args.FunctionGrouping


    # TODO: Restore the working sets from the pickled file - for now, make synthetic ones
    w_set = {}
    addr_base = 0xabcd0000
    for i in range(args.NumFunctions):
        w = []
        for j in range(300):
            w.append(addr_base)
            addr_base += 4
        addr_base -= 0x200 # gives some overlap between each one
        w_set[i] = w

    # Create the simpy environment needed by all components beneath it
    env = Environment()

    # Make latency store from 100ns to 100000ns, precision of 0.01%
    latency_store = HdrHistogram(100,100000,4)

    event_queue = Store(env) # to pass incoming load from generator to balancer

    # Make number of dispatch queues based on function grouping
    if (args.NumFunctions % FuncGrouping) != 0:
        print('ERROR: Cannot evenly divide Num Functions',args.NumFunctions,'into groups of',FuncGrouping,'dying....')
        return {}

    # Create dispatch policy based on static function ID or affinity
    numQueues = args.NumWorkers
    func_queues = [ Store(env) for idx in range(numQueues) ]
    func_policy = SSTDispatch(func_queues)

    # Make the load balancer and load generator
    assert(len(args.FuncPopularities) == args.NumFunctions)
    lgen = NonUniformUServLoadGen(env,event_queue,args.RequestsToSimulate,args.ArrivalRate,args.NumFunctions,args.FuncPopularities)

    # Load balancer for taking requests from the event queue, put into the func queues
    lb = LoadBalancer(env,lgen,event_queue,func_queues,func_policy)

    totalcs = 0
    # For each function group, assign the specified number of cores to it

    # IF dispatch is dynamic affinity based, each core creates ITS OWN function service time generator. Parameters:
    # - working set for a function
    # - number of functions assigned to a core
    # - fraction of library code
    # - boundary for thrashing a prefetcher
    all_cores = []
    for i in range(numQueues):
        core_list = [ DynamicUServCore(env,j,func_queues[i],latency_store,lgen,w_set,
            FuncGrouping,2*1024,args.HistoryDepth) for j in range(args.CoreGrouping) ] # TODO: fix cache size
        totalcs += len(core_list)
        all_cores.extend(core_list)

    func_policy.set_stime_objects(all_cores)
    lb.set_cores(all_cores)

    assert(totalcs == args.NumWorkers)
    env.run()

    # Get results
    rd = {}
    percentiles = [ 50, 70, 90, 95, 99, 99.9 ]
    for p in percentiles:
        rd[p] = float(latency_store.get_value_at_percentile(p)) / 1000 # return in us
    return rd
