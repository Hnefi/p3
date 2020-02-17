#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

# my includes
from components.zipf_gen import ZipfKeyGenerator
from components.load_balancer import LoadBalancerBase
from components.load_generator import PoissonLoadGen

# simpy includes
from my_simpy.src.simpy import Environment
from my_simpy.src.simpy.resources.resource import FiniteQueueResource, Resource
from my_simpy.src.simpy.resources.store import Store

# python environment includes
import argparse
from hdrh.histogram import HdrHistogram

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-N",'--NumItems', type=int,help="Number of items in the dataset. Default = 1M",default = 1000000)
    parser.add_argument("-s",'--ZipfCoeff',type=float,help="Skew (zipf) coefficient. Default = 0.95",default=0.95)
    parser.add_argument('-c','--NumberOfWorkers', dest='NumberOfWorkers', type=int, default=16,help='Number of worker cores in the queueing system. Default = 16')
    parser.add_argument('-A','--Load',type=int,help='Load level for the system. For stability, A < c (number of workers). Default = 1',default=1)
    parser.add_argument('-cp','--ConcurrencyPolicy',required=True,choices=['EREW','CREW','CRCW'])
    parser.add_argument('-f','--WriteFraction',type=int,help='Fraction of writes in the simulation. Default = 0.05 (5%)',default=.05)
    parser.add_argument('--RequestsToSimulate',type=int,help="Number of requests to simulate for. Default = 1M",default = 1000000)
    args = parser.parse_args()

    # Create the simpy environment needed by all components beneath it
    env = Environment()

    # Make the zipf generator
    kwarg_dict = { "num_items" : args.NumItems, "coeff" : args.ZipfCoeff }
    z = ZipfKeyGenerator(**kwarg_dict)
    for i in range(10):
        print('iter',i,'random key rank:',z.get_key())

    # Make the respective queues
    if 'CRCW' in args.ConcurrencyPolicy: # single-queue
        disp_queues = [ Store(env) ]
    else: # both CREW and EREW are a form of multi-queueing
        disp_queues = [ Store(env) for i in range(args.NumberOfWorkers) ]

    # Queue to pass events from generator to balancer
    event_queue = Store(env)

    # Make the load balancer and load generator
    lgen = PoissonLoadGen(env,event_queue,args.RequestsToSimulate,z)
    lb = LoadBalancerBase(env,lgen,event_queue,disp_queues)

    env.run()

if __name__ == '__main__':
    main()
