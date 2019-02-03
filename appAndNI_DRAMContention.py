import argparse
import csv

# Module interfaces
from parallel import Invoker
from interfaces.simpy_interface import SimpyInterface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["sweep_NI"])
    parser.add_argument("--threads", type=int,help="Number of parallel threads to use",default = 1)
    parser.add_argument("--n", type=int,help="Number of rpcs to simulate",default = 10)
    parser.add_argument("--channels", type=int,help="Number of DRAM channels",default = 8)
    parser.add_argument("--cores", type=int,help="Number of cores/RPC servers",default = 8)
    parser.add_argument("--nodes", type=int,help="Number of nodes in the whole system to consider.",default=1000)
    parser.add_argument("mem", help="Type of memory system (affects channel count and total BW)",choices=["DDR4","HBM"])
    args = parser.parse_args()

    def check_arg(arg, msg):
        if not arg:
            parser.print_help()
            raise ValueError(msg)

    from numpy import linspace

    if 'NI' in args.mode:
        if 'HBM' in args.mem:
            invokerArgs = { 'numProcs': int(args.threads),
                            'mode': args.mode,
                            'runnableTarg': SimpyInterface,
                            'NumberOfChannels' : args.channels,
                            'NumberOfCores' : args.cores,
                            'BanksPerChannel' : 32,
                            'BWRange': linspace(10,1000,20),
                            'Servers': args.nodes,
                            'N_rpcs' : args.n
                            }
        else:
            invokerArgs = { 'numProcs': int(args.threads),
                            'mode': args.mode,
                            'runnableTarg': SimpyInterface,
                            'NumberOfChannels' : args.channels,
                            'NumberOfCores' : args.cores,
                            'BanksPerChannel' : 8,
                            'BWRange': linspace(40,800,20),
                            'Servers': args.nodes,
                            'N_rpcs' : args.n
                            }

    threadController = Invoker( **invokerArgs )
    threadController.startProcs()
    threadController.joinProcs()

    results = [ threadController.getResultsFromQueue(idx) for idx in range(int(args.threads)) ]
    flat_results = [ y for x in results for y in x ]
    output_fields = [ str(args.mode.split('_')[1]) ]
    odict = { }

    def init_or_add(d,k,v):
        if k in d:
            d[k].append(v)
        else:
            d[k] = [ v ]

    # Remap to dictwriter-able format.
    for x in flat_results:
        for k,v in x.items():
            n_dropped = v.pop()
            l = sorted(list(v[0]),key = lambda t : t[0])
            #print(k,l,n_dropped)
            for tup in l: #sorted(l,key = lambda t : t[0]):
                if tup[0] not in output_fields: # v[0] is the percentile (e.g., 95th)
                    output_fields.append(tup[0])
                init_or_add(odict,k,tup[1])
        init_or_add(odict,k,n_dropped)

    output_fields.append('n_dropped')

    with open('queueing'+args.mode+'.csv','w') as fh:
        writer = csv.DictWriter(fh, fieldnames = output_fields)
        writer.writeheader()
        for k,v in sorted(odict.items()):
            v.insert(0,k)
            tmp = dict(zip(output_fields,v))
            writer.writerow(tmp)

if __name__ == '__main__':
    main()