from math import floor
from statistics import mean

class ExactLatStore(object):
    def __init__(self):
        self.latencies = []

    def record_value(self,lat):
        self.latencies.append(lat)

    def get_mean(self):
        return mean(self.latencies)

    def get_value_at_percentile(self,perc):
        s = sorted(self.latencies)
        ordinal_num = floor(len(s) * (float(perc)/100))
        return s[ordinal_num]
