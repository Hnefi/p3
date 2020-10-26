import argparse
from numpy import linspace

# Module interfaces
from parallel import Invoker

def main():
    invokerArgs = {'ConcurrencyPolicy' : 'CRCW',
            'runnableTarg' : 'qmodel_dispatch',
            'argrange' : linspace(1,5,1),
            'mode' : 'sweep_A',
            'numProcs': 1}
    threadController = Invoker( **invokerArgs )

    print('starting....')
    threadController.startProcs()

    #join and get res
    threadController.joinProcs()
    print('joined....')

    numProcs = invokerArgs['numProcs']
    results = [ threadController.getResultsFromQueue(idx) for idx in range(numProcs) ]
    flat_results = [ y for x in results for y in x ]
    print(flat_results)

if __name__ == '__main__':
    main()
