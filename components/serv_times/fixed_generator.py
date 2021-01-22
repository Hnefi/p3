#!/usr/bin/python3
## Author: Mark Sutherland, (C) 2020

class FixedServiceTime(object):
    def __init__(self,mean_service_time):
        self.s = mean_service_time

    def get(self):
        return self.s
