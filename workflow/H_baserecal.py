# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class baserecal(Workflow):
    """ baserecal """

    INIT = bundle(baserecal=bundle())
    INIT.baserecal.bqsr = "GaeaBqRecalibrator.jar"
    INIT.baserecal.printreads = "GaeaReadPrinter.jar"
    INIT.baserecal.bqsr_param = "-knownSites file://${dbsnp}"
    INIT.baserecal.printreads_param = ""

    def run(self, impl, dependList):
        impl.log.info("step: baserecal!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.baserecal.bqsr = self.expath('baserecal.bqsr')
        self.baserecal.printreads = self.expath('baserecal.printreads')
        
        if self.option.multiSample:
            self.baserecal.bqsr_param += " -MutiSample "
            
        #global param
        ParamDict = self.file.copy()
        ParamDict.update({
                "PROGRAM_BQSR": "%s jar %s" % (self.hadoop.bin, self.baserecal.bqsr),
                "PROGRAM_PR": "%s jar %s" % (self.hadoop.bin, self.baserecal.printreads),
                "REF": "file://%s" % self.ref.normal.gaeaIndex,
                "REDUCERNUM":self.hadoop.reducer_num
            })
        
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${INPUT}/_*" % fs_cmd.delete )
        cmd.append("%s ${OUTDIR_BQSR}" % fs_cmd.delete )
        cmd.append("${PROGRAM_BQSR} -input ${INPUT} -output ${OUTDIR_BQSR} -ref ${REF} -n ${REDUCERNUM} %s" %self.baserecal.bqsr_param)
        cmd.append("sleep 10")
        cmd.append("%s ${OUTDIR_PR}" % fs_cmd.delete )
        cmd.append("${PROGRAM_PR} -i ${INPUT} -o ${OUTDIR_PR} -f ${REF} -b ${OUTDIR_BQSR}/result.grp %s" %self.baserecal.printreads_param)
        
        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'basequalityrecal_output')
            
            #global param
            JobParamList.append({
                    "SAMPLE" : sampleName,
                    "SCRDIR" : scriptsdir,
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR_BQSR": os.path.join(hdfs_outputPath,"gaeaoutdb"),
                    "OUTDIR_PR": os.path.join(hdfs_outputPath,"printreads")
                })
            
            result.output[sampleName] = os.path.join(hdfs_outputPath,'printreads','result')
            
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'baserecal',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath) 
        return result
                                
