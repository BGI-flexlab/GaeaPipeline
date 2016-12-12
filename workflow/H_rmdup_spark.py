# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class rmdup_spark(Workflow):
    """ rmdup_spark """

    INIT = bundle(rmdup_spark=bundle())
    INIT.rmdup_spark.program = "/ifs4/ISDC_BD/huangzhibo/test/testSpark/20160623/DuplicationMark.jar"
    INIT.rmdup_spark.parameter = ' -i 1 '

    def run(self, impl,dependList):
        impl.log.info("step: rmdup_spark!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.rmdup_spark.program = self.expath('rmdup_spark.program')
        
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${OUTDIR}/" % fs_cmd.delete )
        cmd.append("%s ${INPUT}/*/_SUCCESS ${INPUT}/*/_logs" % fs_cmd.delete )
        cmd.append("spark-submit --class org.bgi.flexlab.gaea.spark.example.DuplicationMark --master yarn --num-executors 48 --driver-memory 8g --executor-memory 25g --executor-cores 4 --queue spark_queue ${PROGRAM} -I ${INPUT} -O ${OUTDIR} ${PARAM}")
            
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'rmdup_spark_output')
            
            #global param
            ParamDict = {
                    "PROGRAM":self.rmdup_spark.program,
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR": hdfs_outputPath,
                    "PARAM":self.rmdup_spark.parameter
                }
            
            #write script
            scriptPath = \
            impl.write_shell(
                    name = 'rmdup_spark',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    paramDict=ParamDict)
            
            #result
            result.output[sampleName] = os.path.join(hdfs_outputPath,'Mark')
            result.script[sampleName] = scriptPath
        return result
                                
