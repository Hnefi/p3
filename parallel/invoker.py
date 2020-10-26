from multiprocessing import Process, Queue
from math import floor

from interfaces.simpy_interface import SimpyInterface

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

        '''
        if 'numservs' in kwargs['mode']:
            argrange = kwargs['coreRange']
            del kwargs['coreRange']
        elif 'numSlots' in kwargs['mode']:
            argrange = kwargs['NumSlots']
            del kwargs['NumSlots']
        elif 'NI' in kwargs['mode']:
            argrange = kwargs['BWRange']
            del kwargs['BWRange']
        '''
        argrange = kwargs['argrange']

        self.queues = [ Queue() for count in range(self.numProcs) ]

        # Divide up jobs and put into queues
        numJobs = len(argrange)
        jobsPerProc = floor(numJobs / self.numProcs)
        extraJobs = numJobs % self.numProcs

        curProc = 0
        maxProc = self.numProcs
        self.jobs_assigned = [ 0 for i in range(self.numProcs) ]
        for job in argrange:
            if self.jobs_assigned[curProc] < jobsPerProc:
                self.queues[curProc].put(job,False) #dont block
                self.jobs_assigned[curProc] += 1
            else:
                curProc += 1
                if curProc >= maxProc :
                    curProc = 0
                self.queues[curProc].put(job,False) #dont block
                self.jobs_assigned[curProc] += 1

        del kwargs['argrange']
        self.processes = [ SimpyInterface( kwargs,self.queues[count],self.jobs_assigned[count],self.runTarg ) for count in range(self.numProcs) ]

    def getResultsFromQueue(self,index):
        resultCount = 0
        results = [ ]
        while resultCount < self.jobs_assigned[index]:
            results.append(self.queues[index].get())
            resultCount += 1
        return results

    def startProcs(self):
        for p in self.processes:
            p.start()

    def joinProcs(self):
        for p in self.processes:
            p.join()
