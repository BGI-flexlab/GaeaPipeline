# encoding: utf-8
import os
import commands

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class BGICGAnnotation(Workflow):
    """ BGICGAnnotation """

    INIT = bundle(BGICGAnnotation=bundle())
    INIT.BGICGAnnotation.bgicgAnno = "/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/BGICG_Annotation/bin/bgicg_anno.pl"
    INIT.BGICGAnnotation.departAnnos = "/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/BGICG_Annotation/bin/depart_annos_v2.pl"
    INIT.BGICGAnnotation.excelReport = "/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/BGICG_Annotation/bin/excel_report_v2.pl"
    INIT.BGICGAnnotation.departAnnos_param = ''
    INIT.BGICGAnnotation.bgicgAnno_param = ''
    INIT.BGICGAnnotation.mem = '4G'

    def run(self, impl,dependList):
        impl.log.info("step: BGICGAnnotation!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.BGICGAnnotation.bgicgAnno = self.expath('BGICGAnnotation.bgicgAnno')
        self.BGICGAnnotation.departAnnos = self.expath('BGICGAnnotation.departAnnos')
        self.BGICGAnnotation.excelReport = self.expath('BGICGAnnotation.excelReport')
        
        annoDir = impl.mkdir(self.option.workdir, "annotation/variation")
        
        if not os.path.exists(self.file.annoProtoclConfig):
            impl.log.error("File: %s is not exists" % self.file.annoProtoclConfig)
        
        self.BGICGAnnotation.bgicgAnno_param = " %s %s" % (self.file.annoProtoclConfig,self.BGICGAnnotation.bgicgAnno_param)
        if self.file.get('MS'):
            self.BGICGAnnotation.bgicgAnno_param = " -i %s -c %s/QC/MS_CHECK.out " % (self.file.get('MS'),self.option.workdir)
        
        _,output =  commands.getstatusoutput('perl %s/bin/require_config.pl %s' % (self.GAEA_HOME,self.file.annoProtoclConfig))
        config = eval(output)
        
        #script template    
        cmd = []
        if os.path.exists('/ifs4/'):
            cmd.append("export BGICGA_HOME=/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/BGICG_Annotation")
            cmd.append("export PATH=/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/HPC_chip/tools:$PATH")
            cmd.append("export HPC_CHIP_HOME=/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/HPC_chip")
            cmd.append("export PERL5LIB=/ifs4/ISDC_BD/data_management/PerlPackages/lib")
            
        cmd.append("${PROGRAM} ${PARAM} ${VCF} -r ${FORMAT} 2> ${LOG}|${DEPART} ${DEPARTPARAM} -p ${OUTPUT}/")
        cmd.append('if [ $? -ne 0 ]; then\n\techo "[WARNING]  ${SAMPLE} - BGICGAnnotation failed." >> %s\n\texit 1\nelse' %self.logfile)
        cmd.append('\techo "[INFO   ]  ${SAMPLE} - BGICGAnnotation complete." >> %s\n\texit 1\nfi\n' % self.logfile)
        
        cmd.append('echo "excel report:${SAMPLE}"')
        cmd.append('cmd=""')
        cmd.append('if [ -e "${OUTPUT}/${SAMPLE}.bed.gz" ]\nthen' )
        cmd.append('\tcmd="$cmd perl ${excelReport} -v ${OUTPUT}/${SAMPLE}.bed.gz -o ${OUTPUT}/${SAMPLE}_vcfanno.xlsm";\n')
        cmd.append('\tcmd="$cmd -r ${filter_rules} -s ${headers} -f ${OUTPUT}/anno.header.format.tsv -b ${vbaProject}"')
        cmd.append('\tif [ -e "${uncovTarget}" ]\n\tthen')
        cmd.append('\t\tcmd="$cmd -u ${uncovTarget}"')
        cmd.append('\t\tif [ -e "${cnvOUT}" ]\n\t\tthen')
        cmd.append('\t\t\tcmd="$cmd -c ${cnvOUT}"')
        cmd.append('\t\tfi\n\tfi\nfi')
        cmd.append('`$cmd`')
        
        cmd.append('if [ $? -ne 0 ]; then\n\techo "[WARNING]  ${SAMPLE} - AnnoExcelReport failed." >> %s\n\texit 1\nelse' %self.logfile)
        cmd.append('\techo "[INFO   ]  ${SAMPLE} - AnnoExcelReport complete." >> %s\nfi' % self.logfile)
       
        ParamDict = {
                "PROGRAM": "perl %s" % self.BGICGAnnotation.bgicgAnno,
                "DEPART": "perl %s" % self.BGICGAnnotation.departAnnos,
                "DEPARTPARAM": self.BGICGAnnotation.departAnnos_param,
                "excelReport": self.BGICGAnnotation.excelReport,
                "PARAM":self.BGICGAnnotation.bgicgAnno_param,
                "filter_rules":config['filter_rules'],
                "headers":config['headers'],
                'vbaProject':config['vbaProject']
            }
        
        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.option.workdir,"scripts",'standalone',sampleName)
            sampleAnnoDir = impl.mkdir(annoDir,sampleName)
            JobParamList.append({
                    "SAMPLE":sampleName,
                    "SCRDIR":scriptsdir,
                    "VCF": inputInfo[sampleName],
                    "FORMAT": os.path.join(annoDir,sampleName,"anno.header.format.tsv"),
                    "OUTPUT": sampleAnnoDir,
                    "uncovTarget" : '%s/QC/graph/uncover_anno/%s.uncover_target.txt' % (self.option.workdir,sampleName),
                    "cnvOUT" : '%s/variation/cnv/%s.CNV.out' % (self.option.workdir,sampleName),
                    "LOG": os.path.join(scriptsdir,"%s_anno.log" % sampleName),
                    "PARAM":self.BGICGAnnotation.bgicgAnno_param
                })
            
            result.output[sampleName] = os.path.join(sampleAnnoDir,'%s.bed.gz'% sampleName)
            
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'BGICGAnnotation',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
        
        #return
        result.script.update(scriptPath)
        return result
                                
