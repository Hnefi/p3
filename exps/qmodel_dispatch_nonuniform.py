#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020

# my includes
from components.load_balancer import LoadBalancer
from components.nonuniform_loadgen import NonUniformUServLoadGen
from components.rpc_core import uServCore, DynamicUServCore
from components.serv_times.userv_function import StaticUServiceTime
from components.dispatch_policies import JBSQDispatchPolicy, FunctionDispatch, AffinityDispatch

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
    parser.add_argument('-T','--FixedTime',type=int,help="Fixed service time which cores always consume (ns). Default = 1000",default=1000)
    parser.add_argument('-W','--WorkingSet',type=int,help="Working set size of a function (KB). Default = 32",default=32*1024)
    parser.add_argument('-S','--CacheSize',type=int,help="Size of an L1 cache. Default = 32",default=32*1024)
    parser.add_argument('-L','--CoreLookahead',type=int,help="Cache block lookahead that the CPU can attain. Default = 1",default=1)
    parser.add_argument('--UseIdealSetup',action='store_true',help="Use ideal setup of single-queue w. best function runtime",default=False)
    parser.add_argument('--HistoryDepth',type=int,help="Depth of per-core RPC history stored by dispatcher. Default = 16",default=16)
    parser.add_argument('--LBThreshold',type=int,help="Threshold for dispatching to shortest queue. Default = 2",default=4)
    parser.add_argument('--UseAffinity',action='store_true',help="Use function-affinity based dispatch",default=False)
    parser.add_argument('--FuncPopularities',type=float,nargs='+',help="A list of floats representing the popularities of each function. Used for load generation. Must be equal to the number of functions.",required=True)
    args = parser.parse_args(arg_string.split())

    # Set this to number of workers or explicitly specified values
    if args.FunctionGrouping == 0:
        FuncGrouping = args.NumWorkers
    else:
        FuncGrouping = args.FunctionGrouping

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
    if args.UseAffinity is True:
        numQueues = args.NumWorkers
        func_queues = [ Store(env) for idx in range(numQueues) ]
        func_policy = AffinityDispatch(func_queues,args.HistoryDepth,args.LBThreshold)
    else:
        numQueues = int(args.NumFunctions/FuncGrouping)
        func_queues = [ Store(env) for idx in range(numQueues) ]
        func_policy = FunctionDispatch(func_queues,FuncGrouping)

    # Make the load balancer and load generator
    assert(len(args.FuncPopularities) == args.NumFunctions)
    lgen = NonUniformUServLoadGen(env,event_queue,args.RequestsToSimulate,args.ArrivalRate,args.NumFunctions,args.FuncPopularities)

    # Load balancer for taking requests from the event queue, put into the func queues
    lb = LoadBalancer(env,lgen,event_queue,func_queues,func_policy)

    # Make the function service time generator. Parameters:
    # - fixed serv time
    # - working set for a function
    # - lookahead to assume
    # - L1 cache size
    # - number of functions assigned to a core
    #fmu_gen = uServiceFunctionTime(args.FixedTime,args.WorkingSet,args.CoreLookahead,args.CacheSize,FuncGrouping)

    # Calculate btb thrashing capacity
    if args.UseIdealSetup is True: # SPECIAL CASE, IDEAL
        funcs_per_btb = args.NumFunctions # fit them all
    else:
        unique_working_set = floor(args.WorkingSet * (1-LIB_FRACTION))
        num_insts = unique_working_set/4
        num_branches = num_insts/5
        funcs_per_btb = floor(6*1024 / float(num_branches))

    totalcs = 0
    # For each function group, assign the specified number of cores to it

    # IF dispatch is dynamic affinity based, each core creates ITS OWN function service time generator. Parameters:
    # - working set for a function
    # - number of functions assigned to a core
    # - fraction of library code
    # - boundary for thrashing a prefetcher
    if args.UseAffinity is True:
        for i in range(numQueues):
            core_list = [ DynamicUServCore(env,j,func_queues[i],latency_store,lgen,args.WorkingSet,FuncGrouping,funcs_per_btb,LIB_FRACTION) for j in range(args.CoreGrouping) ]
            totalcs += len(core_list)
    else:
        fmu_gen = StaticUServiceTime(workset=args.WorkingSet,num_functions=FuncGrouping,
                                       func_thrashing_boundary=funcs_per_btb,library_fraction=LIB_FRACTION)
        for i in range(numQueues):
            core_list = [ uServCore(env,j,func_queues[i],latency_store,fmu_gen,lgen) for j in range(args.CoreGrouping) ]
            totalcs += len(core_list)


    assert(totalcs == args.NumWorkers)
    env.run()

    # Get results
    rd = {}
    percentiles = [ 50, 70, 90, 95, 99, 99.9 ]
    for p in percentiles:
        rd[p] = float(latency_store.get_value_at_percentile(p)) / 1000 # return in us
    return rd
