# encoding: utf-8
import os

from gaeautils import Workflow
from gaeautils import bundle


class rmdup(Workflow):
    """ rmdup """

    INIT = bundle(rmdup=bundle())
    INIT.rmdup.program = "GaeaDuplicateMarker.jar"
    INIT.rmdup.parameter_SE = ' -S '
    INIT.rmdup.parameter = ''

    def run(self, impl,dependList):
        impl.log.info("step: rmdup!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.rmdup.program = self.expath('rmdup.program')
        
        if self.init.get('isSE'):
            self.rmdup.parameter = self.rmdup.parameter_SE
            
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${OUTDIR}/" % fs_cmd.delete )
        cmd.append("%s ${INPUT}/*/_SUCCESS ${INPUT}/*/_logs" % fs_cmd.delete )
        cmd.append("${PROGRAM} -I ${INPUT} -O ${OUTDIR} -i 1 -R ${REDUCERNUM} ${PARAM}")
            
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'rmdup_output')
            
            #global param
            ParamDict = {
                    "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.rmdup.program),
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR": hdfs_outputPath,
                    "REDUCERNUM":self.hadoop.reducer_num,
                    "PARAM":self.rmdup.parameter
                }
            
            #write script
            scriptPath = \
            impl.write_shell(
                    name = 'rmdup',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    paramDict=ParamDict)
            
            #result
            result.output[sampleName] = os.path.join(hdfs_outputPath,'Mark')
            result.script[sampleName] = scriptPath
        return result
                                
