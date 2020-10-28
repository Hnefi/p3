import argparse
from numpy import linspace

# Module interfaces
from parallel import Invoker

def main():
    invokerArgs = {'runnableTarg' : 'qmodel_dispatch',
            #'RequestsToSimulate' : 100000,
            'FunctionGrouping': 4,
            'NumWorkers' : 16,
            'CoreGrouping' : 4,
            'NumFunctions' : 16,
            'argrange' : linspace(200,1000,40),
            'mode' : 'sweep_A',
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
            print(load,*times)

if __name__ == '__main__':
    main()
