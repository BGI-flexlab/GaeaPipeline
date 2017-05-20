# encoding: utf-8
import os

from gaeautils import Workflow
from gaeautils import bundle


class bamqc(Workflow):
    """ bamqc """

    INIT = bundle(bamqc=bundle())
    INIT.bamqc.program = "GaeaBamQC.jar"
    INIT.bamqc.exonDepthSort = "Medicine/exon_sort.pl"
    INIT.bamqc.parameter = ' -M'

    def run(self, impl,dependList):
        impl.log.info("step: bamqc!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.bamqc.program = self.expath('bamqc.program')
        self.bamqc.exonDepthSort = self.expath('bamqc.exonDepthSort',False)
        
        #script template    
        fs_cmd = self.fs_cmd
        cmd = ["export HADOOP_HEAPSIZE=4096"]
        cmd.append("%s ${OUTDIR}" % fs_cmd.delete )
        cmd.append("${PROGRAM} -b ${INPUT} -d ${REF} -o ${OUTDIR} ${REGION} -R ${REDUCERNUM} ${PARAM}")
        cmd.append("#rm exists files:")
        
        if 'newCnv' in self.analysisList:
            if self.bamqc.parameter.find('-C') == -1:
                self.bamqc.parameter += ' -C '

        if self.option.multiSample:
            for sample_name in self.sample:
                cmd.append("rm ${QCDIR}/%s.bam.report.txt ${QCDIR}/%s.unmapped.bed" % (sample_name,sample_name))
                cmd.append("rm ${QCDIR}/%s.insert.xls ${QCDIR}/%s.chromosome.txt"% (sample_name,sample_name))
                cmd.append("rm ${QCDIR}/%s.depth.txt"% sample_name)
                if self.bamqc.parameter.find('-A') != -1:
                    cmd.append("rm -rf ${QCDIR}/%s.anno_region.txt ${QCDIR}/%s.anno_region_low_depth.txt"% (sample_name,sample_name))
                if self.bamqc.parameter.find('-C') != -1:
                    pool = self.sample[sample_name].get('pool')
                    cnvdir = impl.mkdir(self.option.workdir, "variation", 'cnv', pool)
                    if self.hadoop.fs_mode == 'hdfs':
                        cmd.append("\n#cp from hdfs to local:")
                        cmd.append("rm -rf %s/%s*" % (cnvdir,sample_name))
                        cmd.append("%s ${OUTDIR}/cnvDepth/%s* %s" % (fs_cmd.cp,sample_name,cnvdir))
        else:
            cmd.append("rm ${QCDIR}/*bam.report.txt ${QCDIR}/*unmapped.bed" )
            cmd.append("rm ${QCDIR}/*insert.xls ${QCDIR}/*chromosome.txt")
            cmd.append("rm ${QCDIR}/*depth.txt")
            if self.bamqc.parameter.find('-A') != -1:
                cmd.append("rm -rf ${QCDIR}/*anno_region.txt ${QCDIR}/*anno_region_low_depth.txt")
                
        cmd.append("\n#cp from hdfs to local:")
        cmd.append("%s ${OUTDIR}/*report.txt ${QCDIR}" % fs_cmd.cp)
        cmd.append("%s ${OUTDIR}/*unmapped.bed ${QCDIR}" % fs_cmd.cp)
        cmd.append("%s ${OUTDIR}/*insert.xls ${QCDIR}" % fs_cmd.cp)
        cmd.append("%s ${OUTDIR}/*chromosome.txt ${QCDIR}" % fs_cmd.cp)
        cmd.append("%s ${OUTDIR}/*depth.txt ${QCDIR}" % fs_cmd.cp)
        if self.bamqc.parameter.find('-A') != -1:
            cmd.append("%s ${OUTDIR}/*anno_region.txt ${QCDIR}" % fs_cmd.cp)
            cmd.append("%s ${OUTDIR}/*anno_region_low_depth.txt ${QCDIR}" % fs_cmd.cp)
            if self.bamqc.get('exonDepthSort'):
                cmd.append("perl %s ${QCDIR} ${QCDIR}" % self.bamqc.exonDepthSort)
                
            
        #global param
        ParamDict = {
                "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.bamqc.program),
                "REF": "file://%s" % self.ref.normal.gaeaIndex,
                "REGION" : self.file.get('region') and " -g file://%s" % self.file.region or '',
                "REDUCERNUM":self.hadoop.reducer_num,
                "PARAM":self.bamqc.parameter
            }
        
        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'BAMQC_output')
            QCDir = impl.mkdir(self.option.workdir, 'QC', sampleName)
            result.output[sampleName] = QCDir
            
                       
            JobParamList.append({
                    "SAMPLE" : sampleName,
                    "SCRDIR" : scriptsdir,
                    "INPUT": inputInfo[sampleName],
                    "QCDIR" : QCDir,
                    "OUTDIR": hdfs_outputPath
                })
            
    
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'bamqc',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
    
        #result
        result.script.update(scriptPath)
        return result
                                
