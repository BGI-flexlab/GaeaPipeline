# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class bamSort_M(Workflow):
    """ bamSort_M """

    INIT = bundle(bamSort_M=bundle())
    INIT.bamSort_M.program = "hadoop-BamSort.jar"
    INIT.bamSort_M.parameter = "-f 2 -i 2 -ref xx"
    INIT.bamSort_M.picard = "picard.x.1.jar"
    INIT.bamSort_M.output_format = 'file'
    # INIT.bamSort_M.bamindex = False
    
        
    def run(self, impl, dependList):
        impl.log.info("step: bamSort_M!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.bamSort_M.program = self.expath('bamSort_M.program')
        self.bamSort_M.picard = self.expath('bamSort_M.picard')

        reducer = self.hadoop.reducer_num
        if self.option.multiSample:
            redeuce_per_node = 10
            if self.hadoop.is_at_TH:
                redeuce_per_node = 5
            if redeuce_per_node > len(self.sample):
                redeuce_per_node = len(self.sample)
            reducer = int(int(self.hadoop.reducer_num)/redeuce_per_node)
            
        #global param
        ParamDict = {
                "PROGRAM": "%s jar %s -libjars %s" % (self.hadoop.bin, self.bamSort_M.program,self.bamSort_M.picard),
                "REDUCERNUM":reducer
            }
        
        JobParamList = []
        for sampleName in inputInfo:
            hdfs_tmp = os.path.join(self.option.dirHDFS,sampleName,'tmp')
            tmp = impl.mkdir(self.option.workdir,"temp",sampleName)
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            outdir= impl.mkdir(self.option.workdir,"alignment",sampleName)
            
            if self.option.multiSample:
                for sample_name in self.sample:
                    result.output[sample_name] = os.path.join(outdir,"%s.sorted.bam" % sample_name)
            else:
                result.output[sampleName] = os.path.join(outdir,"%s.sorted.bam" % sampleName)
            
            #global param
            JobParamList.append({
                    "SAMPLE" : sampleName,
                    "SCRDIR" : scriptsdir,
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR": 'file://%s' % outdir,
                    "BAMLIST": os.path.join(tmp,"hadoop_bam.list"),
                    "HDFSTMP":hdfs_tmp
                })
            
        #script template    
        fs_cmd = self.fs_cmd
        inputTag = ''
        if dependList[0] == "alignment":
            inputTag = '/*'
        cmd = []
        cmd.append("allparts=")
        cmd.append("%s ${INPUT}%s/part* |awk '{print $%d}' > ${BAMLIST}" % (fs_cmd.ls,inputTag, (not self.hadoop.ishadoop2 and self.hadoop.is_at_TH) and 9 or 8))
        cmd.append('for i in `cat ${BAMLIST}`;do allparts="${allparts} $i";done')
        cmd.append("${PROGRAM} %s -o ${OUTDIR} -r ${REDUCERNUM} ${HDFSTMP} ${allparts}" % self.bamSort_M.parameter)
                    
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'bamSort_M',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath)     
        return result
