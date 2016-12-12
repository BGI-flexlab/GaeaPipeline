# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class evaSNP(Workflow):
    """ evaSNP """

    INIT = bundle(evaSNP=bundle())
    INIT.evaSNP.program = "/ifs4/ISDC_BD/xiaopeng2/products/evaluation/EvaSNP.pl"
    INIT.evaSNP.parameter = ''
    INIT.evaSNP.chip_vcf = ''
    INIT.evaSNP.dbsnp = ''
    INIT.evaSNP.dbsnp_region = ''
    INIT.evaSNP.mem = '5G'

    def run(self, impl, dependList):
        impl.log.info("step: evaSNP!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.evaSNP.program = self.expath('evaSNP.program')
        
        if not self.evaSNP.chip_vcf:
            impl.log.error("No chipVCF value for evaSNP step. please set it.")
        
        #script template    
        cmd = []
        cmd.append("${PROGRAM} ${PARAM} -c ${REFVCF} -r ${VCF} ${DBSNP} -o ${OUTPUT}")
        cmd.append('if [ $? -ne 0 ]; then\n\techo "[WARNING]  ${SAMPLE} - evaSNP failed." >> %s\n\texit 1\nelse' %self.logfile)
        cmd.append('\techo "[INFO   ]  ${SAMPLE} - evaSNP complete." >> %s\n\texit 1\nfi' % self.logfile)
        
        dbsnp = ''
        if self.evaSNP.dbsnp:
            dbsnp = "-d %s" % self.evaSNP.dbsnp
            
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.option.workdir,"scripts",'standalone',sampleName)
            vcf = inputInfo[sampleName]
            outdir = impl.mkdir(self.option.workdir,"QC",'evaVCF',sampleName)
            output = os.path.join(outdir,'evaSNP.txt')
            ParamDict = {
                    "SAMPLE":sampleName,
                    "PROGRAM": "perl %s" % self.evaSNP.program,
                    "REFVCF":self.evaSNP.chip_vcf,
                    "VCF": vcf,
                    "DBSNP" :dbsnp,
                    "OUTPUT": output,
                    "PARAM":self.evaSNP.parameter
                }
            
            #write script
            scriptPath = \
            impl.write_shell(
                    name = 'evaSNP',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    paramDict=ParamDict)
                
            #result
            result.output[sampleName] = output
            result.script[sampleName] = scriptPath
        
        return result
                                
