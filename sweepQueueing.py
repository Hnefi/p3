import argparse
from parallel import Invoker
from interfaces.simpy_interface import SimpyInterface

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["sweep_qdepth", "sweep_numservs"])
    parser.add_argument("--threads", help="Number of parallel threads to use",default = 1)
    args = parser.parse_args()

    def check_arg(arg, msg):
        if not arg:
            parser.print_help()
            raise ValueError(msg)

    invokerArgs = { 'numProcs': int(args.threads),
                    'runnableTarg': SimpyInterface }
    threadController = Invoker( **invokerArgs )
    threadController.startProcs()
    threadController.joinProcs()

if __name__ == '__main__':
    main()
