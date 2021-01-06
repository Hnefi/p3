#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020
# Small hacked file just to test the interface of a module

# Module interfaces
from components.cache_state import FunctionMissModel

from random import randint

# definitions
NUM_FUNCTIONS = 4
HIST_LENGTH = 4

# workset
w_set = {0:20,1:30,2:40,3:80}
sharing = []
init_vec = [0,0,0,0]
for i in range(NUM_FUNCTIONS):
    sharing.append(list(init_vec))

# Generate an upper-triangular matrix representing working set sharing
for x in range(NUM_FUNCTIONS):
    for y in range(NUM_FUNCTIONS):
        if x > y:
            continue
        if x == y:
            sharing[x][y] = w_set[x]
        else:
            # pick random number of a shared working set, up to 50% of the smaller function
            wset_x = w_set[x]
            wset_y = w_set[y]
            smallest = min(wset_y,wset_x)
            sh_set = randint(0,0.5*smallest)
            sharing[x][y] = sh_set
        #print(x,'and',y,'share',sharing[x][y],'KB')
#print(sharing)

c = FunctionMissModel(64,w_set,sharing,HIST_LENGTH)

for x in range(4):
    c.dispatch(x)

c.compute_cache_state()
