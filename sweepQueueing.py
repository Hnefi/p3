import argparse
import csv

# Module interfaces
from parallel import Invoker
from interfaces.simpy_interface import SimpyInterface


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["sweep_qdepth", "sweep_numservs"])
    parser.add_argument("--threads", type=int,help="Number of parallel threads to use",default = 1)
    parser.add_argument("--n", type=int,help="Number of rpcs to simulate",default = 10)
    args = parser.parse_args()

    def check_arg(arg, msg):
        if not arg:
            parser.print_help()
            raise ValueError(msg)

    if 'numservs' in args.mode:
        invokerArgs = { 'numProcs': int(args.threads),
                        'runnableTarg': SimpyInterface,
                        'mode': args.mode,
                        'Lambda' : 0.5,
                        'coreRange': range(400,1000,50),
                        'NumSlots' : 0,
                        'N_rpcs' : args.n,
                        'frac_short' : 1 }
    else:
        invokerArgs = { 'numProcs': int(args.threads),
                        'runnableTarg': SimpyInterface,
                        'mode': args.mode,
                        'Lambda' : 0.5,
                        'NumberOfCores': 1,
                        'NumSlots' : range(0,5),
                        'N_rpcs' : args.n,
                        'frac_short' : 1 }

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
