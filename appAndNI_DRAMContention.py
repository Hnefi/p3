import argparse
import csv

from os.path import isfile
from shutil import copyfile

# Module interfaces
from parallel import Invoker
from interfaces.simpy_interface import SimpyInterface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["sweep_NI"])
    parser.add_argument("mem", help="Type of memory system (affects channel count and total BW)",choices=["DDR4","HBM"])
    parser.add_argument("service_dist", help="Service time distribution that will be implemented by the RPC Generator",choices=["Fixed","Exponential","Bimodal","MICA"])
    parser.add_argument("--threads", type=int,help="Number of parallel threads to use. Default = 1",default = 1)
    parser.add_argument("--n", type=int,help="Number of rpcs to simulate. Default = 10",default = 10)
    parser.add_argument("--channels", type=int,help="Number of DRAM channels. Default = 4",default = 4)
    parser.add_argument("--cores", type=int,help="Number of cores/RPC servers. Default  = 60",default = 60)
    parser.add_argument("--nodes", type=int,help="Number of nodes in the whole system to consider. Default = 1024",default=1024)
    parser.add_argument("--lowBW", type=int,help="Lower bound of network BW to run. Default = 40Gbps",default=40)
    parser.add_argument("--highBW", type=int,help="Upper bound of network BW to run. Default = 1000Gbps",default=1000)
    parser.add_argument("--dataPoints", type=int,help="Number of data points between [lowBW,highBW]. Default = 30",default=30)
    parser.add_argument("--serv_time", type=int,help="Total RPC Service time to model (ns). Default = 425",default=425)
    parser.add_argument("--reqsPerRPC", type=int,help="Number of memory requests per RPC to model. Default = 2",default=2)
    parser.add_argument('--rpcSizeBytes', type=int, default=256,help='Number of bytes making up each RPC\'s argument/return buffer. Default = 256')
    parser.add_argument("--singleBuffer", dest='singleBuffer',default=False, action='store_true',help="If true, use single receive buffer (opportunity study). Default = False")
    parser.add_argument("--printDRAMBW", dest='printDRAMBW',default=False, action='store_true',help="Whether or not to print DRAM BW characteristics post-run.. Default = False")
    parser.add_argument("--micaPrefetch", dest='micaPrefetch',default=False, action='store_true',help="Whether the RPCs themselves model aggressive MICA prefetching.. Default = False")
    parser.add_argument("--dataplanes", dest='dataplanes',default=False, action='store_true',help="If true, model a dataplanes system (N queues x 1). Default = False.")
    parser.add_argument("--collect_qdat", dest='collect_qdat',default=False, action='store_true',help="If true, collect data to measure queue depths and queueing times. Default = False.")
    parser.add_argument("--ofile", dest='ofile',nargs='?',default='qsweep.csv',help="The ouput file to write.")
    parser.add_argument("--odir_qdata", dest='odir_qdata',nargs='?',default='queue_data/',help="The ouput directory to write queueing statstics to.")
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
                            'dist' : args.service_dist,
                            'runnableTarg': SimpyInterface,
                            'NumberOfChannels' : args.channels,
                            'NumberOfCores' : args.cores,
                            'BanksPerChannel' : 32,
                            'BWRange': linspace(args.lowBW,args.highBW,args.dataPoints),
                            'Servers': args.nodes,
                            'serv_time': args.serv_time,
                            'reqsPerRPC': args.reqsPerRPC,
                            'SingleBuffer':args.singleBuffer,
                            'printDRAMBW':args.printDRAMBW,
                            'micaPrefetch':args.micaPrefetch,
                            'rpcSizeBytes':args.rpcSizeBytes,
                            'N_rpcs' : args.n,
                            'collect_qdat' : args.collect_qdat,
                            'dataplanes' : args.dataplanes
                            }
        else:
            invokerArgs = { 'numProcs': int(args.threads),
                            'mode': args.mode,
                            'dist' : args.service_dist,
                            'runnableTarg': SimpyInterface,
                            'NumberOfChannels' : args.channels,
                            'NumberOfCores' : args.cores,
                            'BanksPerChannel' : 24,
                            'BWRange': linspace(args.lowBW,args.highBW,args.dataPoints),
                            'Servers': args.nodes,
                            'serv_time': args.serv_time,
                            'reqsPerRPC': args.reqsPerRPC,
                            'SingleBuffer':args.singleBuffer,
                            'printDRAMBW':args.printDRAMBW,
                            'micaPrefetch':args.micaPrefetch,
                            'rpcSizeBytes':args.rpcSizeBytes,
                            'N_rpcs' : args.n,
                            'collect_qdat' : args.collect_qdat,
                            'dataplanes' : args.dataplanes
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
            avg_bw = v.pop()
            n_dropped = v.pop()
            l = sorted(list(v[0]),key = lambda t : t[0])
            #print(k,l,n_dropped)
            for tup in l: #sorted(l,key = lambda t : t[0]):
                if tup[0] not in output_fields: # v[0] is the percentile (e.g., 95th)
                    output_fields.append(tup[0])
                init_or_add(odict,k,tup[1])
        init_or_add(odict,k,n_dropped)
        init_or_add(odict,k,avg_bw)

    output_fields.append('n_dropped')
    output_fields.append('Avg. DRAM BW')

    # backup old file
    #fstring = 'queueing'+args.mode+'_'+args.mem+'_'+str(args.nodes)+'Nodes'+bstring+'.csv'
    fstring = args.ofile
    if isfile(fstring):
        print(fstring,"already present! Backing up to...",fstring+'.bak')
        copyfile(fstring,fstring+'.bak')

    with open(fstring,'w') as fh:
        writer = csv.DictWriter(fh, fieldnames = output_fields)
        writer.writeheader()
        for k,v in sorted(odict.items()):
            v.insert(0,k)
            tmp = dict(zip(output_fields,v))
            writer.writerow(tmp)

if __name__ == '__main__':
    main()
