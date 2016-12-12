import os

import gaeautils
from gaeautils.bundle import bundle


class JobMonitor(object):
    """ JobMonitor """

    def run(self, state):
        
        if state.option.multiSample:
            pass
        else:
            for sampleName in state.sample.keys():
                scriptsdir = impl.mkdir(self.option.workdir,"scripts",'gaea',sampleName)
                scriptFile = os.path.join(scriptsdir,'gaeaJobMonitor.py') 
                analysisList = gaeautils.getAnalysisList(state.analysis_flow)
                analysisDict = gaeautils.getAnalysisDict(state.analysis_flow)
                script = open(scriptFile, 'w')
                for step in analysisList:
                    #global param
                    ParamDict = {
                        }
                    
                        
                #write script
                scriptPath = \
                impl.write_shell(
                        name = 'JobMonitor',
                        scriptsdir = scriptsdir,
                        commands=cmd,
                        paramDict=ParamDict)
        
        #return
        result.update(scriptPath)
        return result
                                