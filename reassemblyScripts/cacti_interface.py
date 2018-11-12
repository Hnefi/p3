from multiprocessing import Process, Queue

class CactiInterface(Process):
    def __init__(self,*args):
        super().__init__()
        for a in args:
            print(a)

    def run(self):
        print('Called runmethod in process',self.name)
