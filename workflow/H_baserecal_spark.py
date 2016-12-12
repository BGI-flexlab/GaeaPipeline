# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class baserecal_spark(Workflow):
    """ baserecal_spark """

    INIT = bundle(baserecal_spark=bundle())
    INIT.baserecal_spark.bqsr = "/ifs4/ISDC_BD/huweipeng/project/BQSR/GaeaRecalibrationSpark.jar"
    INIT.baserecal_spark.parameter = "-v file:///ifs4/ISDC_BD/GaeaProject/resource/dbsnp_135.hg19.modify.vcf"

    def run(self, impl, dependList):
        impl.log.info("step: baserecal_spark!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.baserecal_spark.bqsr = self.expath('baserecal_spark.bqsr')

        if self.option.multiSample:
            self.baserecal_spark.parameter += " -MutiSample "
            
        #global param
        ParamDict = self.file.copy()
        ParamDict.update({
                "PROGRAM_BQSR": "spark-submit --master yarn --num-executors 192 --executor-cores 1 --executor-memory 6g %s -n 2000" % self.baserecal_spark.bqsr,
                "REF": "file://%s" % self.ref.normal.gaeaIndex
            })
        
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${INPUT}/_*" % fs_cmd.delete )
        cmd.append("%s ${OUTDIR_BQSR}" % fs_cmd.delete)
        cmd.append("${PROGRAM_BQSR} -i ${INPUT} -o ${OUTDIR_BQSR} --ref ${REF} %s" %self.baserecal_spark.parameter)

        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'baserecal_spark_output')
            
            #global param
            JobParamList.append({
                    "SAMPLE" : sampleName,
                    "SCRDIR" : scriptsdir,
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR_BQSR": hdfs_outputPath
                })
            
            result.output[sampleName] = hdfs_outputPath
            
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'baserecal_spark',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath) 
        return result
                                
