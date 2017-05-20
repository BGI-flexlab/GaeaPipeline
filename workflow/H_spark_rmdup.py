# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class spark_rmdup(Workflow):
    """ spark_rmdup """

    INIT = bundle(spark_rmdup=bundle())
    INIT.spark_rmdup.program = "/ifs4/ISDC_BD/huangzhibo/test/testSpark/20160623/DuplicationMark.jar"
    INIT.spark_rmdup.parameter = ' -i 1 '

    def run(self, impl,dependList):
        impl.log.info("step: spark_rmdup!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.spark_rmdup.program = impl.expath(self.Path.prgDir, self.spark_rmdup.program)
        
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${OUTDIR}/" % fs_cmd.delete )
        cmd.append("%s ${INPUT}/*/_SUCCESS ${INPUT}/*/_logs" % fs_cmd.delete )
        cmd.append("spark-submit --class org.bgi.flexlab.gaea.spark.example.DuplicationMark --master yarn --num-executors 48 --driver-memory 8g --executor-memory 25g --executor-cores 4 --queue spark_queue ${PROGRAM} -I ${INPUT} -O ${OUTDIR} ${PARAM}")
            
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'spark_rmdup_output')
            
            #global param
            ParamDict = {
                    "PROGRAM":self.spark_rmdup.program,
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR": hdfs_outputPath,
                    "PARAM":self.spark_rmdup.parameter
                }
            
            #write script
            scriptPath = \
            impl.write_shell(
                    name = 'spark_rmdup',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    paramDict=ParamDict)
            
            #result
            result.output[sampleName] = os.path.join(hdfs_outputPath,'Mark')
            result.script[sampleName] = scriptPath
        return result
                                
