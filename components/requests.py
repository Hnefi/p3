#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

## A class that implements an abstract request type
class AbstractRequest(object):
    def __init__(self):
        pass

## A class that models an RPC request
class RPCRequest(AbstractRequest):
    def __init__(self,rpc_number):
        super().__init__()
        self.num = rpc_number
        self.dispatch_time = -1
        self.start_proc_time = -1
        self.end_proc_time = -1
        self.completion_time = -1

    def getQueuedTime(self):
        return self.start_proc_time - self.dispatch_time

    def getProcessingTime(self):
        return self.end_proc_time - self.start_proc_time

    def getTotalServiceTime(self):
        return self.completion_time - self.dispatch_time
