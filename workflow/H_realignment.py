# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class realignment(Workflow):
    """ realignment """

    INIT = bundle(realignment=bundle(),ref=bundle(normal=bundle()))
    INIT.realignment.program = "GaeaRealigner.jar"
    INIT.realignment.parameter = ''

    def run(self, impl, dependList):
        impl.log.info("step: realignment!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.realignment.program = self.expath('realignment.program')
        
        if self.option.multiSample:
            self.realignment.parameter += " --mutiSample"
            
        #global param
        ParamDict = self.file.copy()
        ParamDict.update({
                "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.realignment.program),
                "REF": "file://%s" % self.ref.normal.gaeaIndex,
                "REDUCERNUM":self.hadoop.reducer_num
            })
            
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${OUTDIR}" % fs_cmd.delete )
        cmd.append("%s ${INPUT}/_*" % fs_cmd.delete )
        cmd.append("${PROGRAM} --align ${INPUT} --out ${OUTDIR} --ref ${REF} --reducer ${REDUCERNUM} %s" %self.realignment.parameter)
        
        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'realignment_output')
            
            #global param
            JobParamList.append({
                    "SAMPLE" : sampleName,
                    "SCRDIR" : scriptsdir,
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR": hdfs_outputPath
                })
                    
            result.output[sampleName] = os.path.join(hdfs_outputPath,'FixMateResult')
            
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'realignment',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath) 
        return result
                                
