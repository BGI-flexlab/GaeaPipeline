# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class mergeVariant(Workflow):
    """ mergeVariant """

    INIT = bundle(mergeVariant=bundle())
    INIT.mergeVariant.sort = "vcf-sort"
    INIT.mergeVariant.merge = "vcfmerge.pl"
#    INIT.mergeVariant.filter = "Medicine/vcf_snp_indel_filter.pl"
    INIT.mergeVariant.filter = ""
    INIT.mergeVariant.split = "Medicine/vcf_sample_split.pl"
    INIT.mergeVariant.filter_param = '-snp "QD<2.0 || MQ<40.0 || FS>60.0 || HaplotypeScore>13.0 || MQRankSum<-12.5 || ReadPosRankSum<-8.0" -indel "ReadPosRankSum<-20.0 ||InbreedingCoeff<-0.8 || FS>200.0"'
    INIT.mergeVariant.output_format = ''


    def run(self, impl, dependList):
        impl.log.info("step: mergeVariant!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.mergeVariant.sort = self.expath('mergeVariant.sort')
        self.mergeVariant.merge = self.expath('mergeVariant.merge')
        self.mergeVariant.filter = self.expath('mergeVariant.filter',False)
        self.mergeVariant.split = self.expath('mergeVariant.split',False)
        
        tmp = impl.mkdir(self.option.workdir,"temp")

        vcf_suffix = 'GaeaGenotyper.sorted.vcf'

        if self.option.multiSample and self.genotype.parameter.find('noMultiSampleCall') != -1:
            sampleName = self.option.multiSampleName
            outputPath = impl.mkdir(self.option.workdir,"variation",'genotype',sampleName)
            scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
            
            #global param
            ParamDict = {
                    "INPUT": inputInfo[sampleName],
                    "OUTDIR": outputPath,
                    "GENOTYPE" : impl.mkdir(self.option.workdir,"temp",sampleName),
                    "TMP": tmp,
                    "SORT" : self.mergeVariant.sort
                }
            #script template    
            fs_cmd = self.fs_cmd
            cmd = []
            cmd.append("mkdir -p ${GENOTYPE}/genotype/")
            cmd.append("rm -rf ${GENOTYPE}/genotype/*")
            cmd.append("rm -rf ${OUTDIR}/*")
            cmd.append("%s ${INPUT}/*.vcf ${GENOTYPE}/genotype/" % fs_cmd.cp)
            cmd.append("for i in ${GENOTYPE}/genotype/*.vcf;do mv -f $i `echo $i | sed s/.vcf$//g`;done")
            cmd.append('for i in ${GENOTYPE}/genotype/*;do cat $i | ${SORT} -t ${TMP} >${OUTDIR}/`basename $i`.sorted.vcf;done')
            if self.init.bgzip:
                cmd.append('for i in ${OUTDIR}/*.sorted.vcf;do %s -f $i;done'% self.init.bgzip)
                vcf_suffix = 'GaeaGenotyper.sorted.vcf.gz'
                if self.mergeVariant.filter:
                    cmd.append('for i in ${OUTDIR}/*.sorted.vcf.gz;do perl %s $i `echo $i|sed s/.vcf.gz$//g`.filter.vcf.gz %s;done' % (self.mergeVariant.filter, self.mergeVariant.filter_param))
                    vcf_suffix = 'GaeaGenotyper.sorted.filter.vcf.gz'
            #write script
            scriptPath = \
            impl.write_shell(
                    name = 'mergeVariant',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    paramDict=ParamDict)
            
            #result
            for sample_name in self.sample:
                result.output[sample_name] = os.path.join(outputPath,'%s.%s' % (sample_name,vcf_suffix))
            result.script[sampleName] = scriptPath
        else:
            #script template    
            fs_cmd = self.fs_cmd
            cmd = []
            cmd.append("mkdir -p ${GENOTYPE}/genotype/")
            cmd.append("rm -rf ${GENOTYPE}/genotype/*")
            cmd.append("rm -rf ${GENOTYPE}/GaeaGenotyper.vcf")
            cmd.append("rm -rf ${OUTDIR}/*")
            cmd.append("allVariations=")
            cmd.append("%s ${INPUT}/vcf/part* ${GENOTYPE}/genotype" % fs_cmd.cp)
            cmd.append('if [ "`ls ${GENOTYPE}/genotype`" = "" ];then\n\techo "[WARNING]  ${SAMPLE} - mergeVariant failed." >> %s\n\texit 1\nfi' %self.logfile )
            cmd.append("for i in `ls ${GENOTYPE}/genotype`;do")
            cmd.append('\tallVariations="${allVariations} ${GENOTYPE}/genotype/$i"\ndone')
            cmd.append("perl ${MERGE} ${allVariations} >${GENOTYPE}/GaeaGenotyper.vcf")
            cmd.append("cat ${GENOTYPE}/GaeaGenotyper.vcf|${SORT} -t ${TMP} >${OUTDIR}/${SAMPLE}.GaeaGenotyper.sorted.vcf")
            if self.init.bgzip:
                cmd.append('rm ${OUTDIR}/${SAMPLE}.GaeaGenotyper.sorted.vcf.gz')
                cmd.append('%s -f ${OUTDIR}/${SAMPLE}.GaeaGenotyper.sorted.vcf'% self.init.bgzip)
                vcf_suffix = 'GaeaGenotyper.sorted.vcf.gz'
                if self.mergeVariant.filter:
                    cmd.append('rm ${OUTDIR}/${SAMPLE}.GaeaGenotyper.sorted.filter.vcf.gz')
                    cmd.append('perl %s ${OUTDIR}/${SAMPLE}.GaeaGenotyper.sorted.vcf.gz ${OUTDIR}/${SAMPLE}.GaeaGenotyper.sorted.filter.vcf.gz %s' % (self.mergeVariant.filter, self.mergeVariant.filter_param))
                    vcf_suffix = 'GaeaGenotyper.sorted.filter.vcf.gz'

            for sampleName in inputInfo:
                outputPath = impl.mkdir(self.option.workdir,"variation",'genotype',sampleName)
                scriptsdir = os.path.join(self.gaeaScriptsDir,sampleName)
                #global param
                ParamDict = {
                        "SAMPLE":sampleName,
                        "INPUT": inputInfo[sampleName],
                        "OUTDIR": outputPath,
                        "GENOTYPE" : impl.mkdir(self.option.workdir,"temp",sampleName),
                        "TMP": tmp,
                        "SORT" : self.mergeVariant.sort,
                        "MERGE" : self.mergeVariant.merge
                    }
        
                #write script
                scriptPath = \
                impl.write_shell(
                        name = 'mergeVariant',
                        scriptsdir = scriptsdir,
                        commands=cmd,
                        paramDict=ParamDict)
                
                #result
                result.output[sampleName] = os.path.join(outputPath,'%s.%s' % (sampleName,vcf_suffix))
                result.script[sampleName] = scriptPath
                
        return result
                                
