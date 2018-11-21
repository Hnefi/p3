import argparse
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
                        'coreRange': range(500,1200,100),
                        'NumSlots' : 0,
                        'N_rpcs' : args.n,
                        'f' : 0.9 }
    else:
        invokerArgs = { 'numProcs': int(args.threads),
                        'runnableTarg': SimpyInterface,
                        'mode': args.mode,
                        'Lambda' : 0.5,
                        'coreRange': 1000,
                        'NumSlots' : range(0,1000,100),
                        'N_rpcs' : args.n,
                        'f' : 0.9 }

    threadController = Invoker( **invokerArgs )
    threadController.startProcs()
    threadController.joinProcs()

if __name__ == '__main__':
    main()
