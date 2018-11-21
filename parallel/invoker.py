from multiprocessing import Process, Queue
from math import floor

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
        del kwargs['runnableTarg']
        del kwargs['numProcs']

        if 'numservs' in kwargs['mode']:
            argrange = kwargs['coreRange']
            del kwargs['coreRange']
        else:
            argrange = kwargs['NumSlots']
            del kwargs['NumSlots']

        self.queues = [ Queue() for count in range(self.numProcs) ]

        # Divide up jobs and put into queues
        numJobs = len(argrange)
        jobsPerProc = floor(numJobs / self.numProcs)
        extraJobs = numJobs % self.numProcs

        curProc = 0
        maxProc = self.numProcs
        jobs_assigned = [ 0 for i in range(self.numProcs) ]
        for job in argrange:
            if jobs_assigned[curProc] < jobsPerProc:
                self.queues[curProc].put(job,False) #dont block
                jobs_assigned[curProc] += 1
            else:
                curProc += 1
                if curProc >= maxProc :
                    curProc = 0
                self.queues[curProc].put(job,False) #dont block
                jobs_assigned[curProc] += 1

        self.processes = [ self.runTarg( kwargs,self.queues[count],jobs_assigned[count] ) for count in range(self.numProcs) ]

    def getDatafromObjectQueue(self,index):
        pass

    def startProcs(self):
        for p in self.processes:
            p.start()

    def joinProcs(self):
        for p in self.processes:
            p.join()
