# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class filter(Workflow):
    """ A Fastq Clean stage before alignment"""

    INIT = bundle(filter=bundle())
    INIT.filter.program = 'GaeaFastqQC.jar'
    INIT.filter.parameter = '-Q 0 -lowQual 11 -qualRate 0.1'

    def run(self, impl, dependList):
        impl.log.info("step: filter!")
        #此处 dependList == ['init']
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())
        
        #extend program path
        self.filter.program = self.expath('filter.program')
        self.filter.parameter = impl.paramCheck(True,self.filter.parameter,'-Q',str(self.init.qualitySystem))
        
        if int(self.init.qualitySystem) == 0:
            self.filter.parameter = impl.paramCheck(False,self.filter.parameter,'-C')
        
        #global param
        ParamDict = {
                "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.filter.program)
            }
        
        parameter = self.filter.parameter
        parameter += " -reduceNum %s " % self.hadoop.reducer_num
        
        fs_cmd = self.fs_cmd
        #sample parameter array
        if self.option.multiSample:
            sampleName = self.option.multiSampleName
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'filter')
            QCDir = impl.mkdir(self.option.workdir, 'QC', sampleName)
            scriptsdir = impl.mkdir(self.option.workdir,"scripts",'gaea',sampleName)
            sampleInputInfo = inputInfo[sampleName]
            output = bundle()

            JobParam = []
            if self.ref.gender_mode == "both" and self.option.mode != 5:
                if self.info.female_counter > 0:
                    sampleinfo = sampleInputInfo.female
                    outdir = os.path.join(hdfs_outputPath,'female')
                    output.female = os.path.join(outdir,'out_fq')
                    JobParam.append({
                        "SAMPLELIST": 'file://' + sampleinfo,
                        "OUTDIR": outdir,
                        "QCDIR": QCDir,
                        "OPTIONPARAM": parameter
                    })
                if self.info.male_counter > 0:
                    sampleinfo = sampleInputInfo.male
                    outdir = os.path.join(hdfs_outputPath,'male')
                    output.male = os.path.join(outdir,'out_fq')
                    JobParam.append({
                        "SAMPLELIST": 'file://' + sampleinfo,
                        "OUTDIR": outdir,
                        "QCDIR" : QCDir,
                        "OPTIONPARAM": parameter
                    })
            elif self.ref.gender_mode == "normal" or self.option.mode == 5:
                sampleinfo = sampleInputInfo.normal
                outdir = hdfs_outputPath
                output.normal = os.path.join(outdir,'out_fq')
                JobParam.append({
                    "SAMPLELIST": 'file://' + sampleinfo,
                    "OUTDIR": outdir,
                    "QCDIR": QCDir,
                    "OPTIONPARAM": parameter
                })


            cmd = []
            cmd.append("%s ${OUTDIR}" % fs_cmd.delete)
            cmd.append("${PROGRAM} -m ${SAMPLELIST} -outdir ${OUTDIR} ${OPTIONPARAM}")
            cmd.append("%s ${OUTDIR}/*filter.report.txt ${QCDIR}" % fs_cmd.cp)
            cmd.append("%s ${OUTDIR}/*graph.data.txt ${QCDIR}" % fs_cmd.cp)
            cmd.append("%s ${OUTDIR}/out_fq/_*\n" % fs_cmd.delete)

            #write script
            scriptPath = \
                impl.write_shell(
                    name = 'filter',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    JobParamList=JobParam,
                    paramDict=ParamDict)

            result.output[sampleName] = output
            result.script[sampleName] = scriptPath
        else:
            for sampleName in inputInfo.keys():
                QCDir = impl.mkdir(self.option.workdir, 'QC', sampleName)
                scriptsdir = os.path.join(self.gaeaScriptsDir,sampleName)
                hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'filter')
                sampleInputInfo = inputInfo[sampleName]
                output = bundle()
                JobParam = []
                
                for dataTag in sampleInputInfo:
                    hdfs_outDir = os.path.join(hdfs_outputPath,sampleName+"-"+dataTag+"_fq")
                    
                    adp = ''
                    if sampleInputInfo[dataTag].has_key('adp1'):
                        adp = " -adapter1 file://%s" % sampleInputInfo[dataTag]['adp1']
                    if sampleInputInfo[dataTag].has_key('adp2'):
                        adp += " -adapter2 file://%s" % sampleInputInfo[dataTag]['adp2']
                    parameterStr = "%s %s" % (adp,parameter)
                    output[dataTag] = os.path.join(hdfs_outDir,'out_fq')
                    
                    if self.init.isSE == False:
                        JobParam.append({
                            "DATATAG":dataTag,
                            "FQ1": 'file://' + sampleInputInfo[dataTag]['fq1'],
                            "FQ2": 'file://' + sampleInputInfo[dataTag]['fq2'],
                            "OUTDIR": hdfs_outDir,
                            "FREPORT": os.path.join(QCDir, sampleName+'.'+dataTag+'.filter.report.txt'),
                            "GREPORT": os.path.join(QCDir, sampleName+'.'+dataTag+'.graph.data.txt'),
                            "OPTIONPARAM":parameterStr
                        })       
                    else:
                        JobParam.append({
                            "DATATAG":dataTag,
                            "FQ1": 'file://' + sampleInputInfo[dataTag]['fq1'],
                            "OUTDIR": hdfs_outDir,
                            "FREPORT": os.path.join(QCDir, sampleName+'.'+dataTag+'.filter.report.txt'),
                            "GREPORT": os.path.join(QCDir, sampleName+'.'+dataTag+'.graph.data.txt'),
                            "OPTIONPARAM":parameterStr
                        })
            
                cmd = []
                cmd.append('echo "filter %s-${DATATAG}"'% sampleName)
                cmd.append("%s ${OUTDIR}" % fs_cmd.delete )
                if self.init.isSE:
                    cmd.append("${PROGRAM} -in1Fq ${FQ1} -outdir ${OUTDIR}  ${OPTIONPARAM}")
                else:
                    cmd.append("${PROGRAM} -in1Fq ${FQ1} -in2Fq ${FQ2} -outdir ${OUTDIR}  ${OPTIONPARAM}")
                
                cmd.append("%s ${OUTDIR}/filter.report.txt ${FREPORT}" % fs_cmd.cp )
                cmd.append("%s ${OUTDIR}/graph.data.txt ${GREPORT}" % fs_cmd.cp ) 
                cmd.append("%s ${OUTDIR}/out_fq/_*" % fs_cmd.delete)
                
                #write script
                scriptPath = \
                impl.write_shell(
                        name = 'filter',
                        scriptsdir = scriptsdir,
                        commands=cmd,
                        JobParamList=JobParam,
                        paramDict=ParamDict)
                
                result.output[sampleName] = output
                result.script[sampleName] = scriptPath
                
        return result