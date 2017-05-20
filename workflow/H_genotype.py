# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class genotype(Workflow):
    """ genotype """

    INIT = bundle(genotype=bundle())
    INIT.genotype.program = "GaeaGenotyper.jar"
    INIT.genotype.parameter = "-genotype_likelihoods_model BOTH  -stand_call_conf 30.0 -stand_emit_conf 10.0 -dbsnp file:///ifs4/ISDC_BD/GaeaProject/resource/dbsnp_135.hg19.modify.vcf"

    def run(self, impl, dependList):
        impl.log.info("step: genotype!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.genotype.program = self.expath('genotype.program')
        
        if not self.option.multiSample:
            if self.genotype.parameter.find('-noMultiSampleCall') != -1:
                impl.log.warning("Pipeline is in single sample mode, disable -noMultiSampleCall. (deleted)")
                self.genotype.parameter = self.genotype.parameter.replace('-noMultiSampleCall','')
                
        if self.file.get("regionVariation"):
            self.genotype.parameter += " -intervals file://%s " % self.file.regionVariation
        elif self.file.get("region"):
            self.genotype.parameter += " -intervals file://%s " % self.file.region
            
        #global param
        ParamDict = self.file.copy()
        ParamDict.update({
                "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.genotype.program),
                "REF": "file://%s" % self.ref.normal.gaeaIndex,
                "REDUCERNUM":self.hadoop.reducer_num
            })
        
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${INPUT}/_*" % fs_cmd.delete )
        cmd.append("%s ${OUTDIR}" % fs_cmd.delete )
        cmd.append("${PROGRAM} -input ${INPUT} -out ${OUTDIR} -ref ${REF} -reduceNum ${REDUCERNUM} %s" %self.genotype.parameter )
        
        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'genotype_output')
            result.output[sampleName] = hdfs_outputPath
            
            #global param
            JobParamList.append({
                    "SAMPLE" : sampleName,
                    "SCRDIR" : scriptsdir,
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR": hdfs_outputPath
                })
            
    
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'genotype',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath)           
        return result
                                
