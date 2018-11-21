from multiprocessing import Process, Queue
from .tlat_sim import simulate

class SimpyInterface(Process):
    def __init__(self,*args):
        super().__init__()
        for a in args:
            print(a)

    def run(self):
        print('Called run method in Simpy interface process',self.name)
