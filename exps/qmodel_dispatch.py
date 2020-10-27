#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020

# my includes
from components.load_balancer import LoadBalancer
from components.userv_loadgen  import uServLoadGen
from components.rpc_core import uServCore
from components.serv_times.userv_function import uServiceFunctionTime
from components.dispatch_policies import JBSQDispatchPolicy, FunctionDispatch

# simpy includes
from my_simpy.src.simpy import Environment
from my_simpy.src.simpy.resources.store import Store

# python environment includes
import argparse
from hdrh.histogram import HdrHistogram

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
    args = parser.parse_args(arg_string.split(' '))

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

    numQueues = int(args.NumFunctions / FuncGrouping)
    func_queues = [ Store(env) for idx in range(numQueues) ]
    # Create dispatch policy based on function ID
    func_policy = FunctionDispatch(func_queues,FuncGrouping)

    # Make the load balancer and load generator
    lgen = uServLoadGen(env,event_queue,args.RequestsToSimulate,args.ArrivalRate,args.NumFunctions)

    # Load balancer for taking requests from the event queue, put into the func queues
    lb = LoadBalancer(env,lgen,event_queue,func_queues,func_policy)

    # Make the function service time generator. Parameters:
    # - fixed serv time
    # - working set for a function
    # - lookahead to assume
    # - L1 cache size
    # - number of functions assigned to a core
    fmu_gen = uServiceFunctionTime(args.FixedTime,args.WorkingSet,args.CoreLookahead,args.CacheSize,FuncGrouping)

    totalcs = 0
    # For each function group, assign the specified number of cores to it
    for i in range(numQueues):
        core_list = [ uServCore(env,j,func_queues[i],latency_store,fmu_gen,lgen) for j in range(args.CoreGrouping) ]
        totalcs += len(core_list)

    assert(totalcs == args.NumWorkers)
    #print('Running queueing study... Input queues:',numQueues,'Num cores per q:',
            #args.CoreGrouping,'Num functions per core:',FuncGrouping)

    env.run()

    # Get results
    def getServiceTimes(latStore):
        percentiles = [ 50, 95, 99, 99.9 ]
        vals = [ latStore.get_value_at_percentile(p) for p in percentiles ]
        return zip(percentiles,vals)

    zipped_results = getServiceTimes(latency_store)
    return zipped_results
