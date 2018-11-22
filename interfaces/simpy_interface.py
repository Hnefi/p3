from multiprocessing import Process, Queue
from queue import Empty
from .tlat_sim import simulate

def conv_to_string(k,v):
    return "--" + str(k) + " " + str(v)

def build_arg_string(d):
    elems = [ conv_to_string(k,v) for (k,v) in d.items() ]
    ret = ''
    for i in elems:
        ret += i
        ret += ' '
    return ret

class SimpyInterface(Process):
    def __init__(self,simpy_arguments,q,num_jobs):
        super().__init__()
        self.kwargs = dict(simpy_arguments)
        self.workQ = q
        self._njobs = num_jobs
        self.mode = self.kwargs['mode']
        del self.kwargs['mode']
        self.simpy_argstring = build_arg_string(self.kwargs)

    def run(self):
        jobs = [ ]
        while len(jobs) < self._njobs:
            try:
                jobs.append( self.workQ.get(True,10) )
            except Empty:
                print('Could not get a job from workQ for 10 seconds, smth is wrong...')
                return

        # should always get here
        print("Thread", self.name, "starting work.")
        while len(jobs) > 0:
            strToPass = self.simpy_argstring
            job_id = jobs.pop()
            if 'numservs' in self.mode:
                addMe = '-k ' + str(job_id)
                strToPass += addMe
            else:
                addMe = '--NumSlots ' + str(job_id)
                strToPass += addMe

            # Run it.
            output = simulate(strToPass)
            self.workQ.put( {job_id : output}, False ) # nowait
