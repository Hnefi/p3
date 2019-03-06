from math import floor

class CondorScriptGenerator(object):
    def __init__(self,**kwargs):
        if "condorBase" not in kwargs.keys():
            raise ValueError("Condor script generator requested without a condor base file.")

        if "runnableTarg" not in kwargs.keys():
            raise ValueError("runnableTarg argument not specified in Invoker")
        else:
            self.runTarg = kwargs['runnableTarg']
        del kwargs['runnableTarg']

        if 'numservs' in kwargs['mode']:
            argrange = kwargs['coreRange']
            del kwargs['coreRange']
        elif 'numSlots' in kwargs['mode']:
            argrange = kwargs['NumSlots']
            del kwargs['NumSlots']
        elif 'NI' in kwargs['mode']:
            argrange = kwargs['BWRange']
            del kwargs['BWRange']

    def readBaseFile(self):
        pass

    def createCondorScript(self):
        # get the base template
        condor_file = self.readBaseFile( kwargs['condorBase'] )

        # divide up the jobs and create a cmd for each one
        for job in argrange:
            pass

        #
