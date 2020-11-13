import argparse
from numpy import linspace
from random import shuffle

# Module interfaces
from parallel import Invoker
from components.zipf_gen import ZipfKeyGenerator

def main():
    # Add to dictionary the function popularities assumed (use a zipf for now)
    NUM_FUNCTIONS = 16
    zargs = { 'num_items' : NUM_FUNCTIONS, 'coeff' : 0.9}
    zgen = ZipfKeyGenerator(**zargs)
    pdf_array = [ zgen.prob_for_rank(i) for i in range(NUM_FUNCTIONS) ]
    shuffle(pdf_array)

    def make_string_from_pop_list(l):
        ostring = ""
        for x in l:
            ostring += str(x) + " "
        return ostring

    invokerArgs = {'runnableTarg' : 'qmodel_dispatch_nonuniform',
            'RequestsToSimulate' : 100000,
            'FuncPopularities' : make_string_from_pop_list(pdf_array),
            'FunctionGrouping': 16,
            #'FunctionGrouping': 4,
            'NumWorkers' : 16,
            'CoreGrouping' : 1,
            #'CoreGrouping' : 4,
            'NumFunctions' : NUM_FUNCTIONS,
            'argrange' : linspace(350,1000,1),
            'mode' : 'sweep_A',
            'UseAffinity' : '',
            'WorkingSet' : 24*1024,
            'numProcs': 2}
    threadController = Invoker( **invokerArgs )

    threadController.startProcs()

    #join and get res
    threadController.joinProcs()

    numProcs = invokerArgs['numProcs']
    results = [ threadController.getResultsFromQueue(idx) for idx in range(numProcs) ]
    flat_results = [ y for x in results for y in x ]
    for x in flat_results:
        for load,times in x.items():
            print(load,times)

if __name__ == '__main__':
    main()
