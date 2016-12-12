# encoding: utf-8
from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow
import os
import shutil


class cgConversion(Workflow):
    """ cgConversion """

    INIT = bundle(cgConversion=bundle())
    INIT.cgConversion.program = "GaeacgConversion.jar"
    INIT.cgConversion.parameter = ""

    def run(self, impl, dependList):
        impl.log.info("step: cgConversion!")
        # depend  1:bamSort  2:mergeVariant
        bamInfo = self.results[dependList[0]].output
        inputInfo = self.results[dependList[1]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.cgConversion.program = self.expath('cgConversion.program')
        
        bams = os.path.join(self.option.workdir,'temp','bams')
        if os.path.exists(bams):
            shutil.rmtree(bams)
        impl.mkdir(bams)
        
        for sample in bamInfo:
            bamname = os.path.basename(bamInfo[sample])
            bam = os.path.join(bams,bamname)
            os.symlink(bamInfo[sample], bam)
                
        if self.file.get("region"):
            self.cgConversion.parameter += " -g file://%s " % self.file.region
            
        #global param
        ParamDict = self.file.copy()
        ParamDict.update({
                "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.cgConversion.program),
                "GAEAINDEX": "file://%s" % self.ref.normal.gaeaIndex,
                "BAM":"file://%s" % bams,
                "REDUCERNUM":self.hadoop.reducer_num
            })
        
        
        #JobParam or each script
        JobParamList = []
        if self.option.multiSample and self.genotype.parameter.find('-noMultiSampleCall') != -1:
            vcfs = os.path.join(self.option.workdir,'temp','vcfs')
            if os.path.exists(vcfs):
                shutil.rmtree(vcfs)
            impl.mkdir(self.option.workdir,'temp','vcfs')
            
            for sampleName in inputInfo:
                vcfname = os.path.basename(inputInfo[sampleName])
                vcf = os.path.join(vcfs,vcfname)
                os.symlink(inputInfo[sampleName], vcf)
                
            multi_sample = self.option.multiSampleName
            output = impl.mkdir(self.option.workdir,'CG',multi_sample)
            JobParamList.append({
                    "SAMPLE" : self.option.multiSampleName,
                    "SCRDIR" : impl.mkdir(self.gaeaScriptsDir,multi_sample),
                    "INPUT": 'file://%s' % vcfs,
                    "HDFSOUTDIR": os.path.join(self.option.dirHDFS,multi_sample,'cgConversion'),
                    "OUTPUT":output
                })
        else:
            for sampleName in inputInfo:
                scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
                hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'cgConversion')
                output = impl.mkdir(self.option.workdir,'CG',sampleName)
                result.output[sampleName] = output
                
                JobParamList.append({
                        "SAMPLE" : sampleName,
                        "SCRDIR" : scriptsdir,
                        "INPUT": 'file://%s' % inputInfo[sampleName],
                        "HDFSOUTDIR": hdfs_outputPath,
                        "OUTPUT":output
                    })
            
        #script template    
        fs_cmd = self.fs_cmd
        cmd = []
        cmd.append("%s ${INPUT}/_*" % fs_cmd.delete )
        cmd.append("%s ${HDFSOUTDIR}" % fs_cmd.delete )
        cmd.append("${PROGRAM} -b ${BAM} -o ${HDFSOUTDIR} -R ${REDUCERNUM} -d  ${GAEAINDEX} -v ${INPUT} %s" %self.cgConversion.parameter )
        cmd.append('\n%s ${HDFSOUTDIR}/annotated-var* ${OUTPUT}' % fs_cmd.cp)
    
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'cgConversion',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath)           
        return result
                                
