#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020

# my includes
from components.zipf_gen import ZipfKeyGenerator

# python environment includes
import argparse
import hashlib

def init_or_append_to_dict(d,k,v):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]

parser = argparse.ArgumentParser()
parser.add_argument("-N",'--NumItems', type=int,help="Number of items in the dataset. Default = 1M",default = 1000000)
parser.add_argument("-s",'--ZipfCoeff',type=float,help="Skew (zipf) coefficient. Default = 0.95",default=0.95)
parser.add_argument("-p",'--NumPartitions',type=int,help="Number of partitions to calculate skew between. Default = 16",default=16)
args = parser.parse_args()


# Make the zipf generator
kwarg_dict = { "num_items" : args.NumItems, "coeff" : args.ZipfCoeff }
z = ZipfKeyGenerator(**kwarg_dict)

partitions = {}
partition_probs = [ ]
for p in range(args.NumPartitions):
    partition_probs.append(0.0)

# Partition all key ranks into buckets, randomly using hashes
for rank in range(args.NumItems):
    m = hashlib.sha256()
    m.update(str(rank).encode('utf-8'))
    final_4B = m.hexdigest()[-8:]
    bucket = int(final_4B,16) % args.NumPartitions

    init_or_append_to_dict(partitions,bucket,rank)
    partition_probs[bucket] += z.prob_for_rank(rank)

# Calculate prob skew
hottest = 0.0
for p in partition_probs:
    if p > hottest:
        hottest = p

avg_load = sum(partition_probs) / len(partition_probs)
print("Partition probabilities:",partition_probs,"Total prob:",sum(partition_probs))
print("Hottest partition has:",hottest,"of load, for skew factor of:",hottest / avg_load)
