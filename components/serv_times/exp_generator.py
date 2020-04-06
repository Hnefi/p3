#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

from numpy.random import exponential
class ExpServTimeGenerator(object):
    def __init__(self,mean_service_time):
        self.exp_stime = mean_service_time

    def get(self):
        return exponential(self.exp_stime)
