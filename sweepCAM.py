import argparse
from parallel import Invoker
from interfaces import CactiInterface

def main():
    parser = argparse.ArgumentParser()
    #parser.add_argument("mode", choices=["author-keys", "paper-lists",
                                         #"list-co-authors", "get-conflicts"])
    parser.add_argument("--threads", help="Number of parallel threads to use",default = 1)
    args = parser.parse_args()

    def check_arg(arg, msg):
        if not arg:
            parser.print_help()
            raise ValueError(msg)

    invokerArgs = { 'numProcs': int(args.threads),
                    'runnableTarg': CactiInterface }
    threadController = Invoker( **invokerArgs )
    threadController.startProcs()
    threadController.joinProcs()

if __name__ == '__main__':
    main()
