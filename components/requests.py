#!/usr/bin/env python
## Author: Mark Sutherland, (C) 2020

import hashlib

## A class that implements an abstract request type
class AbstractRequest(object):
    def __init__(self):
        pass

## A class that models an RPC request
class RPCRequest(AbstractRequest):
    def __init__(self,rpc_number,k,write=False):
        super().__init__()
        self.num = rpc_number
        self.key = k
        self.dispatch_time = -1
        self.start_proc_time = -1
        self.end_proc_time = -1
        self.completion_time = -1
        self.isWrite = write

        self.h_obj = hashlib.sha256()
        self.h = self.h_obj.update(bytes(self.key))

    def __hash__(self):
        return self.h

    def getQueuedTime(self):
        return self.start_proc_time - self.dispatch_time

    def getProcessingTime(self):
        return self.end_proc_time - self.start_proc_time

    def getTotalServiceTime(self):
        return self.completion_time - self.dispatch_time

    def getWrite(self):
        return self.isWrite

    def setWrite(self):
        self.isWrite = True

## A class that models an rpc processor asking the load balancer for a new request
class PullFeedbackRequest(AbstractRequest):
    def __init__(self,proc_num):
        super().__init__()
        self.proc_id = proc_num

    def getID(self):
        return self.proc.id
