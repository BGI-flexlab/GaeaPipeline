# encoding: utf-8
import commands
from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow
import os


class cnv(Workflow):
    """ cnv """

    INIT = bundle(cnv=bundle())
    INIT.cnv.program = ""
    INIT.cnv.parameter = ""

    def run(self, impl, dependList):
        impl.log.info("step: cnv!")
        # depend bamQC
        inputInfo = self.results[dependList[0]].output
        result = bundle(script=bundle())
        
        multi_sample = self.option.multiSampleName
        scriptsdir = impl.mkdir(self.option.workdir,"scripts",'standalone',multi_sample)
        
        #extend program path
        self.cnv.program = self.expath('cnv.program')
                
        temp = impl.mkdir(self.option.workdir,'temp') 
        annolist = os.path.join(temp,'anno_depth.list')
        with open(annolist,'w') as f:
            if self.option.multiSample:
                for sample in self.sample:
                    anno_region = os.path.join(inputInfo[multi_sample],'%s.anno_region.txt' % sample)
                    line = "%s\t%s\n" % (sample,anno_region)
                    f.write(line)
            else:
                for sampleName in inputInfo:
                    anno_region = os.path.join(inputInfo[sampleName],'%s.anno_region.txt' % sampleName)
                    line = "%s\t%s\n" % (sampleName,anno_region)
                    f.write(line)
                    
        _,output =  commands.getstatusoutput('perl %s/bin/require_config.pl %s' % (self.GAEA_HOME,self.file.annoProtoclConfig))
        config = eval(output)
        self.cnv.parameter += ' -trans %s' % config['trans']   
        
        #global param
        ParamDict = {
                "PROGRAM": "perl %s" % self.cnv.program,
                "OUTPUT" : impl.mkdir(self.option.workdir,'variation','cnv'),
                "ANNOLIST":annolist,
                "SAMPLELIST": self.option.sampleList
            }
        
        #script template    
        cmd = ["${PROGRAM} -output ${OUTPUT} -QC ${ANNOLIST} -samplelist ${SAMPLELIST}  %s" %self.cnv.parameter]
    
        #write script
        scriptPath = \
        impl.write_shell(
                name = 'cnv',
                scriptsdir = scriptsdir,
                commands=cmd,
                paramDict=ParamDict)
    
        #result
        result.script[multi_sample] = scriptPath    
        return result
