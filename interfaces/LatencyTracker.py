from numpy import digitize, ceil
from math import floor

# Exact tail latency tracker
class ExactLatencyTracker(object):
    def __init__(self):
        self.values = []

    def record_value(self,latency):
        self.values.append(latency)

    def get_value_at_percentile(self,percentile):
        if len(self.values) > 0:
            lsort = sorted(self.values)
            idx = floor(len(self.values) * float(percentile/100))
            return lsort[idx]
        else:
            return 0.0

# Tail latency tracker, using bins and linear interpolation
class BinLatencyTracker(object):
    def __init__(self,baseBinValueNs,TailCut):
        self.baseLatency = baseBinValueNs
        self.maxTailLatency = TailCut
        self.totalDataPoints = 0
        self.bins = []
        self.binBounds = []
        tmpValue = baseBinValueNs
        while tmpValue < TailCut:
            tmpValue += 25
            self.binBounds.append(tmpValue)
            self.bins.append(0)
        self.binBounds.append(TailCut*1000000) # all other shit goes here
        self.bins.append(0)

    def getBinNumberGivenLatency(self,lat):
        test = digitize(lat,self.binBounds,True) # true for right interval closed
        #print("Latency:",lat,"Bins:",self.binBounds,"Index:",test)
        return test

    def record_value(self,latency):
        self.bins[self.getBinNumberGivenLatency(latency)] += 1
        self.totalDataPoints += 1

    def get_value_at_percentile(self,percentile):
        # construct cumulative count and percentiles covered
        cumulativeCountArray = []
        binPercentiles = []
        runningTotal = 0
        for index in range(len(self.bins)):
            runningTotal += self.bins[index]
            cumulativeCountArray.append(runningTotal)
            binPercentiles.append(runningTotal / float(self.totalDataPoints))

        # check where the ordinal-th value would fall
        ordinalOfDesiredPercentile = ceil(self.totalDataPoints * float(percentile/100))
        binNumber = digitize(ordinalOfDesiredPercentile,cumulativeCountArray,True)
        print("We want the",percentile,"th \% latency, so this is the",ordinalOfDesiredPercentile,"measurement out of",self.totalDataPoints,"total recorded")
        #print("Running totals:",cumulativeCountArray)
        #print("Bin percentiles:",binPercentiles)
        #print("Bin number chosen:",binNumber)
        if( binNumber == (len(cumulativeCountArray)-1) ):
            print("WARNING: Latency fell in bin number",binNumber,"WHICH IS THE LAST BIN. Suggest rerun or parameter change.")
            return self.binBounds[binNumber]
        else:
            #print("Bin number: ", binNumber,"out of", len(self.binBounds))
            #print("Lower bound:",self.binBounds[binNumber-1],"Upper bound:",self.binBounds[binNumber])
            #print("Upper bound percentile:",binPercentiles[binNumber])
            #print("Low bound percentile:",binPercentiles[binNumber-1])
            lowerBound = self.binBounds[binNumber-1]
            slope = (self.binBounds[binNumber] - self.binBounds[binNumber-1])
            fract = float(percentile - (100*binPercentiles[binNumber-1])) / float(100*binPercentiles[binNumber] - 100*binPercentiles[binNumber-1])
            print("Fract:",fract)
            return lowerBound + (slope*fract)


