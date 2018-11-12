from multiprocessing import Process, Queue

class Invoker(object):
    def __init__(self,**kwargs):
        if "numProcs" not in kwargs.keys():
            raise ValueError("numProcs argument not specified in Invoker")
        else:
            self.numProcs = kwargs['numProcs']
        if "runnableTarg" not in kwargs.keys():
            raise ValueError("runnableTarg argument not specified in Invoker")
        else:
            self.runTarg = kwargs['runnableTarg']

        self.queues = [ Queue() for count in range(self.numProcs) ]
        self.processes = [ self.runTarg( 'a',1,{},self.queues[count] ) for count in range(self.numProcs) ]

    def getDatafromObjectQueue(self,index):
        pass

    def startProcs(self):
        for p in self.processes:
            p.start()

    def joinProcs(self):
        for p in self.processes:
            p.join()
