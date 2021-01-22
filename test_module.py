#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
# Small hacked file just to test the interface of a module

# Module interfaces
from components.cache_state import FunctionMissModel

from random import randint

# definitions
NUM_FUNCTIONS = 4
HIST_LENGTH = 2

# workset
w_set = {}
# Generate a dict with each func having a list of addresses
addr_base = 0xabcd0000
for i in range(NUM_FUNCTIONS):
    w = []
    for j in range(300):
        w.append(addr_base)
        addr_base += 4
    addr_base -= 0x200 # gives some overlap between each one
    w_set[i] = w

c = FunctionMissModel(2*1024,w_set,HIST_LENGTH)

for x in range(4):
    c.dispatch(x)
for x in range(4):
    print('new function number',x,'expects',c.get_misses_for_function(x),'misses')
