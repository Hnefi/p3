#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
# Small hacked file just to test the interface of a module

# Module interfaces
from components.cache_state import FunctionMissModel

# definitions
NUM_FUNCTIONS = 4
HIST_LENGTH = 4

# workset
w_set = {0:20,1:30,2:40,3:80}
sharing = []
for x in range(NUM_FUNCTIONS):
    sharing.append([])
    #TODO: have to create a diagonally symmetric matrix here

c = FunctionMissModel(64,w_set,sharing,HIST_LENGTH)

for x in range(4):
    c.dispatch(x)

c.compute_cache_state()
