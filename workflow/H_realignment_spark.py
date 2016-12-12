# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class realignment_spark(Workflow):
    """ realignment_spark """

    INIT = bundle(realignment_spark=bundle(),ref=bundle(normal=bundle()))
    INIT.realignment_spark.program = "/ifs4/ISDC_BD/huangzhibo/test/testSpark/20160623/GaeaRealignment_debug_0_3_5_3.jar"
    INIT.realignment_spark.parameter = ''

    def run(self, impl, dependList):
        impl.log.info("step: realignment_spark!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.realignment_spark.program = self.expath('realignment_spark.program')
        
        if self.option.multiSample:
            self.realignment_spark.parameter += " --mutiSample"
            
        #global param
        ParamDict = self.file.copy()
        ParamDict.update({
                "PROGRAM": "%s" % self.realignment_spark.program,
                "REF": "file://%s" % self.ref.normal.gaeaIndex
            })
            
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append('LIB="/ifs4/ISDC_BD/huangzhibo/test/testSpark/20160623/sparklib"')
        cmd.append("%s ${OUTDIR}" % fs_cmd.delete )
        cmd.append("%s ${INPUT}/_*" % fs_cmd.delete )
        cmd.append("spark-submit \\")
        cmd.append("--class org.bgi.flexlab.gaea.GaeaRealigner.GaeaRealigner \\")
        cmd.append("--name GaeaRealignment \\")
        cmd.append("--master yarn \\")
        cmd.append("--num-executors 48 \\")
        cmd.append("--driver-memory 8g \\")
        cmd.append("--executor-memory 25G \\")
        cmd.append("--executor-cores 5 \\")
        cmd.append("--executor-cores 5 \\")
        cmd.append('--conf spark.network.timeout=600 \\') 
        cmd.append('--conf spark.speculation=true \\') 
        cmd.append('--conf spark.speculation.quantile=0.75 \\') 
        cmd.append('--conf spark.speculation.multiplier=1.5 \\') 
        cmd.append('--conf spark.storage.memoryFraction=0.15 \\') 
        cmd.append('--conf spark.storage.unrollFraction=1.0 \\') 
        cmd.append('--conf spark.shuffle.memoryFraction=0.5 \\') 
        cmd.append('--conf "spark.executor.extraJavaOptions=-XX:+UseG1GC -XX:+PrintFlagsFinal -verbose:gc -XX:+PrintGCDetails -XX:+PrintGCTimeStamps -XX:+UnlockDiagnosticVMOptions -XX:+G1SummarizeConcMark -XX:InitiatingHeapOccupancyPercent=45" \\') 
        cmd.append('--queue spark_queue \\') 
        cmd.append('--jars \\') 
        cmd.append('$LIB/cofoja-1.0-r139.jar,\\') 
        cmd.append('$LIB/jopt-simple-4.3.jar,\\') 
        cmd.append('$LIB/tribble.jar,\\') 
        cmd.append('$LIB/commons-jexl-2.1.1.jar,\\') 
        cmd.append('$LIB/snappy-java-1.0.3-rc3.jar \\') 
        cmd.append('${PROGRAM} \\') 
        cmd.append('--align ${INPUT} \\') 
        cmd.append('--ref file://${REF} \\') 
        cmd.append('--out ${OUTDIR} \\') 
        cmd.append('--hadoopConf "mapreduce.input.fileinputformat.split.minsize=40000000 mapreduce.input.fileinputformat.split.maxsize=40000000" \\') 
        cmd.append('--s1PartitionNum 48000 \\') 
        cmd.append('--s2PartitionNum 0 %s' % self.realignment_spark.parameter) 
        
        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'realignment_spark_output')
            
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
                name = 'realignment_spark',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath) 
        return result
                                
