# Python class to calculate conflict probabilities for nebula paper
# Howtouse:
#   - Initialize it with a **kwargs containing the keys nSets, nWays, and nT
#   - call calc_probs which will return the config dictionary and the final pConf
from scipy.special import binom as binomCoeff

class ProbCalculator(object):
    def __init__(self,**kwargs):
        # args needed from higher level:
        #   (nSets,nWays) -> Parameterize reassembler
        #   (nT) -> number of outstanding requests
        if "nSets" not in kwargs.keys():
            raise ValueError("Required nSets argument not specified in ProbCalculator")
        if "nWays" not in kwargs.keys():
            raise ValueError("Required nWays argument not specified in ProbCalculator")
        if "nT" not in kwargs.keys():
            raise ValueError("Required nT argument not specified in ProbCalculator")

        self.theConfig = { "nSets": kwargs["nSets"],
                            "nWays": kwargs["nWays"],
                            "nT" : kwargs["nT"] }

    def calc_probs(self):
        S = self.theConfig["nSets"]
        W = self.theConfig["nWays"]
        T = self.theConfig["nT"]
        WForConflict = W+1
        singleSetProb = binomCoeff(T,WForConflict) * (1/(float(S**WForConflict)))
        ubound = S * float(singleSetProb)
        #print("for S,W,T = ",S,W,T,"the single set prob is ",singleSetProb,"and the ubound is",ubound)
        r = self.theConfig
        r['Pconf'] = ubound
        return r
