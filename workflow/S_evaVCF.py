# encoding: utf-8
from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class evaVCF(Workflow):
    """ evaVCF """

    INIT = bundle(evaVCF=bundle())
    INIT.evaVCF.program = "/home/huangzhibo/script/vcfeval.py"
    INIT.evaVCF.parameter = ''
    INIT.evaVCF.ref = '/ifs4/ISDC_BD/huangzhibo/Data/ref/hg19_chM_male_mask.fa.sdf'
    INIT.evaVCF.chip_vcf = ''
    INIT.evaVCF.dbsnp = ''
    INIT.evaVCF.test_bed = ''
    INIT.evaVCF.ref_bed = ''
    INIT.evaVCF.mem = '5G'

    def run(self, impl, dependList):
        impl.log.info("step: evaVCF!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.evaVCF.program = self.expath('evaVCF.program')
        
        if not self.evaVCF.chip_vcf:
            impl.log.error("No chipVCF value for evaVCF step. please set it.")
        
        #script template    
        cmd = []
        cmd.append("${PROGRAM} ${PARAM} -c ${REFVCF} -r ${VCF} ${TESTBED} ${REFBED} -o ${OUTPUT}")
        cmd.append('if [ $? -ne 0 ]; then\n\techo "[WARNING]  ${SAMPLE} - evaVCF failed." >> %s\n\texit 1\nelse' %self.logfile)
        cmd.append('\techo "[INFO   ]  ${SAMPLE} - evaVCF complete." >> %s\n\texit 1\nfi' % self.logfile)
        
        
        dbsnp = ''
        if self.evaVCF.dbsnp:
            dbsnp = "-d %s" % self.evaVCF.dbsnp
        test_bed =''
        if self.evaVCF.get('test_bed'):
            test_bed = "--test-bed=%s" % self.evaVCF.test_bed
            
        ref_bed=''
        if self.evaVCF.get('ref_bed'):
            ref_bed = "--ref-bed=%s" % self.evaVCF.ref_bed
            
        ParamDict = {
                "PROGRAM": "python %s" % self.evaVCF.program,
                "REFVCF":self.evaVCF.chip_vcf,
                "DBSNP":dbsnp,
                "TESTBED":test_bed,
                "REFBED":ref_bed,
                "PARAM":self.evaVCF.parameter
            }
        
        JobParamList = []   
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.option.workdir,"scripts",'standalone',sampleName)
            output = impl.mkdir(self.option.workdir,"QC",'evaVCF',sampleName)
            vcf = inputInfo[sampleName]
            JobParamList.append({
                    "SCRDIR":scriptsdir,
                    "SAMPLE":sampleName,
                    "REFVCF":self.evaVCF.chip_vcf,
                    "VCF": vcf,
                    "OUTPUT": output
                })
            
        #write script
        scriptPath = \
        impl.write_scripts(
                name = 'evaVCF',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)
        
        #return
        result.script.update(scriptPath)
        return result
                                
