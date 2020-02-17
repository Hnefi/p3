#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

## A class that implements an abstract request type
class AbstractRequest(object):
    def __init__(self):
        pass

## A class that models an RPC request
class RPCRequest(AbstractRequest):
    def __init__(self):
        super().__init__()
