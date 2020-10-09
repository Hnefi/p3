#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020

# my includes
from components.zipf_gen import ZipfKeyGenerator
from components.uni_gen import UniformKeyGenerator
from components.load_balancer import LoadBalancer
from components.load_generator import PoissonLoadGen
from components.rpc_core import RPCCore
from components.serv_times.exp_generator import ExpServTimeGenerator
from components.dispatch_policies import RandomDispatchPolicy, JSQDispatchPolicy, JBSQDispatchPolicy, CREWDispatchPolicy, EREWDispatchPolicy

# simpy includes
from my_simpy.src.simpy import Environment
from my_simpy.src.simpy.resources.store import Store

# python environment includes
import argparse
from hdrh.histogram import HdrHistogram

def run_exp(arg_string):
    parser = argparse.ArgumentParser()
    parser.add_argument("-N",'--NumItems', type=int,help="Number of items in the dataset. Default = 1M",default = 1000000)
    parser.add_argument("-s",'--ZipfCoeff',type=float,help="Skew (zipf) coefficient. If set to 0, uniform distribution. Default = 0.95",default=0.95)
    parser.add_argument('-c','--NumberOfWorkers', dest='NumberOfWorkers', type=int, default=16,help='Number of worker cores in the queueing system. Default = 16')
    parser.add_argument('-A','--Load',type=float,help="Load level for the system. For stability, A < c (number of workers). Default = 1",default=1.0)
    parser.add_argument('-cp','--ConcurrencyPolicy',required=True,choices=['EREW','CREW','CRCW'],help="Concurrency dispatch policy")
    parser.add_argument('-f','--WriteFraction',type=float,help="Fraction of writes in the simulation, expressed as percentage. Default = 5",default=5.0)
    parser.add_argument('--RequestsToSimulate',type=int,help="Number of requests to simulate for. Default = 1M",default = 1000000)
    args = parser.parse_args()

    # Create the simpy environment needed by all components beneath it
    env = Environment()

    # Make the zipf generator
    kwarg_dict = { "num_items" : args.NumItems, "coeff" : args.ZipfCoeff }
    if args.ZipfCoeff == 0:
        z = UniformKeyGenerator(**kwarg_dict)
        #print('Using uniform key ranks....')
    else:
        z = ZipfKeyGenerator(**kwarg_dict)
        #print('Using skewed key ranks.... Displaying 20 examples.')
        #for i in range(20):
            #print('key',i,'has rank:',z.get_key())


    # Make latency store from 1 to 1000, precision of 0.01%
    latency_store = HdrHistogram(1, 1000, 4)

    # Make the respective queues and cores
    if 'CRCW' in args.ConcurrencyPolicy: # single-queue
        disp_queues = [ Store(env) ]
        disp_policy = JSQDispatchPolicy(disp_queues)
    else: # both CREW and EREW are a form of multi-queueing
        disp_queues = [ Store(env) for i in range(args.NumberOfWorkers) ]
        if 'CREW' in args.ConcurrencyPolicy:
            disp_policy = CREWDispatchPolicy(disp_queues)
        else: # EREW
            disp_policy = EREWDispatchPolicy(disp_queues)

    event_queue = Store(env) # to pass incoming load from generator to balancer

    # Make the load balancer and load generator
    lgen = PoissonLoadGen(env,event_queue,args.RequestsToSimulate,z,args.Load,args.WriteFraction)
    lb = LoadBalancer(env,lgen,event_queue,disp_queues,disp_policy)

    rd_generator = ExpServTimeGenerator(1.0)
    wr_generator = ExpServTimeGenerator(1.5)

    # Hook up cores
    if 'CRCW' in args.ConcurrencyPolicy: # single-queue
        core_list = [ RPCCore(env,i,disp_queues[0],latency_store,rd_generator,wr_generator,lgen) for i in range(args.NumberOfWorkers) ] # All get a single queue
    else: # private core queues
        core_list = [ RPCCore(env,i,disp_queues[i],latency_store,rd_generator,wr_generator,lgen) for i in range(args.NumberOfWorkers) ]  # Multi-queue

    #print('Running for',args.RequestsToSimulate,'requests......')
    env.run()

    # Get results
    def getServiceTimes(latStore):
        percentiles = [ 50, 95, 99, 99.9 ]
        vals = [ latStore.get_value_at_percentile(p) for p in percentiles ]
        return zip(percentiles,vals)

    zipped_results = getServiceTimes(latency_store)
    print(*zipped_results)
