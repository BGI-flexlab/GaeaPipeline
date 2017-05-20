# encoding: utf-8
import os

from gaeautils import Workflow
from gaeautils import bundle


class bamSort(Workflow):
    """ bamSort """

    INIT = bundle(bamSort=bundle())
    INIT.bamSort.program = "hadoop-bam-x.7.0.jar"
    INIT.bamSort.picard = "picard.x.1.jar"
    INIT.bamSort.output_format = 'file'
    # INIT.bamSort.bamindex = False
    
        
    def run(self, impl, dependList):
        impl.log.info("step: bamSort!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.bamSort.program = self.expath('bamSort.program')
        self.bamSort.picard = self.expath('bamSort.picard')

        reducer = self.hadoop.reducer_num
        if self.option.multiSample:
            redeuce_per_node = 10
            # if self.hadoop.is_at_TH:
            #     redeuce_per_node = 5
            if redeuce_per_node > len(self.sample):
                redeuce_per_node = len(self.sample)
            reducer = int(int(self.hadoop.reducer_num)/redeuce_per_node)
            
        #global param
        ParamDict = {
                "PROGRAM": "%s jar %s -libjars %s" % (self.hadoop.bin, self.bamSort.program,self.bamSort.picard),
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
        cmd = []
        cmd.append("allparts=")
        cmd.append("%s ${INPUT}/part* |awk '{print $%d}' > ${BAMLIST}" % (fs_cmd.ls, (not self.hadoop.ishadoop2 and self.hadoop.is_at_TH) and 9 or 8))
        cmd.append('for i in `cat ${BAMLIST}`;do allparts="${allparts} $i";done')
        cmd.append("${PROGRAM} sort -F BAM -o ${OUTDIR} --reducers ${REDUCERNUM} ${HDFSTMP} ${allparts} &")
                    
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'bamSort',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath)     
        return result
