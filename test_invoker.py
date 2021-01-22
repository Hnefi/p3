import argparse
from numpy import linspace
from random import shuffle

# Module interfaces
from parallel import Invoker
from components.zipf_gen import ZipfKeyGenerator

def main():
    # Add to dictionary the function popularities assumed (use a zipf for now)
    NUM_FUNCTIONS = 16
    zargs = { 'num_items' : NUM_FUNCTIONS, 'coeff' : 0}
    zgen = ZipfKeyGenerator(**zargs)
    pdf_array = [ zgen.prob_for_rank(i) for i in range(NUM_FUNCTIONS) ]
    shuffle(pdf_array)

    def make_string_from_pop_list(l):
        ostring = ""
        for x in l:
            ostring += str(x) + " "
        return ostring

    invokerArgs = {'runnableTarg' : 'serv_time_predictor',
            'argrange' : linspace(350,1000,1),
            'mode' : 'file_based',
            'numProcs': 1}
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
