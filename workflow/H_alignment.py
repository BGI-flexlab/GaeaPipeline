# encoding: utf-8
import os
import shutil

from gaeautils import Workflow
from gaeautils import bundle


class alignment(Workflow):
    """ alignment (bwa) """

    INIT = bundle(alignment=bundle())
    INIT.alignment.program = "bwa-0.7.10-streaming"
    INIT.alignment.bwaSubTool = 'aln'
    INIT.alignment.streamingJar = "Streaming_fq.jar"
    INIT.alignment.parameter = ''
    INIT.alignment.defaultbwaThreadsNum = 6 
    INIT.alignment.fqInputFormat = "org.bgi.flexlab.hadoop.format.fastq.FqText"
    INIT.alignment.fqInputPartitionKey = 2
    INIT.alignment.fqInputOutputKey = 3
    INIT.alignment.bwaReducerMem = ''
    INIT.alignment.bwaReducerNum = ''
    INIT.alignment.bwaReducerNumDivide = ''
    
    def run(self, impl, dependList):
        impl.log.info("step: alignment!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(),script=bundle())

        #program path extend
        self.alignment.program = self.expath('alignment.program')
        self.alignment.streamingJar = self.expath('alignment.streamingJar')

        #TODO nofilter
        tmpInputInfo = bundle()
        fastqDir = impl.mkdir(self.option.workdir,'raw_data','fastq')

        if self.alignment.bwaReducerMem:
            hadoop2_reducer_mem = self.alignment.bwaReducerMem
        elif self.hadoop.is_at_TH:
            hadoop2_reducer_mem = '20480'
        else:
            #hadoop2_reducer_mem = '7168'
            hadoop2_reducer_mem = '20480'

        if self.alignment.bwaReducerNumDivide:
            pass
        elif self.hadoop.is_at_TH:
            self.alignment.bwaReducerNumDivide = 5
        else:
            self.alignment.bwaReducerNumDivide = 3

        if not self.alignment.get('bwaReducerNum'):
            self.alignment.bwaReducerNum = int(self.hadoop.reducer_num)/int(self.alignment.bwaReducerNumDivide)
        if self.alignment.bwaReducerNum < 1:
            self.alignment.bwaReducerNum = 1 

        hadoop_param = '-D mapred.map.tasks=%s ' % str(self.hadoop.mapper_num)
        hadoop_param += '-D mapred.reduce.tasks=%s ' % str(self.alignment.bwaReducerNum)
        if self.hadoop.get('ishadoop2'):
            hadoop_param += '-D mapreduce.reduce.memory.mb=%s ' % hadoop2_reducer_mem
        hadoop_param += "-D stream.num.map.output.key.fields=%s " % self.alignment.fqInputOutputKey
        hadoop_param += "-D num.key.fields.for.partition=%s " % self.alignment.fqInputPartitionKey
        hadoop_param += "-libjars=%s " % self.alignment.streamingJar
        hadoop_param += "-partitioner org.apache.hadoop.mapred.lib.KeyFieldBasedPartitioner "
        hadoop_param += "-inputformat %s" % self.alignment.fqInputFormat
        ParamDict = {
            "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.hadoop.streamingJar),
            "MAPPER": '"/bin/cat"'
        }

        if int(self.init.qualitySystem) != 0:
            if self.analysisDict.has_key('filter'):
                if self.filter.parameter.rfind('-C') != -1:
                    self.init.qualitySystem = '0'
                    impl.log.info("quality system is changed to '0'.")

        rg_param_tag = '-r'
        if self.alignment.bwaSubTool.rfind('mem') != -1:
            rg_param_tag = '-R'
            samplelistparam = '-X'
            subfunc = 'mem'
            if self.init.isSE:
                subfunc += ' -p '
            if int(self.init.qualitySystem) != 0:
                impl.log.error("quality system is not sanger. BWA mem don't support non-sanger quality system! Please set -C in filter parameter.")
        else:
            samplelistparam = '-T'
            subfunc = 'alnpe'
            if self.init.isSE:
                subfunc = 'alnse'
            if int(self.init.qualitySystem) == 1:
                self.alignment.parameter = impl.paramRectify(self.alignment.parameter,'-I',True)
            else:
                self.alignment.parameter = impl.paramRectify(self.alignment.parameter,'-I',False)

        if not self.alignment.parameter.rfind('-t ') != -1:
            self.alignment.parameter += ' -t %s ' %  str(self.alignment.defaultbwaThreadsNum)


        fs_cmd = self.fs_cmd
        #sample parameter array
        if self.option.multiSample:
            if dependList[0] == 'init':
                raise RuntimeError("Cann't run this Pipeline in multi-smaple mode without filter step now.")
                for sampleName in inputInfo:
                    tmpInputInfo[sampleName] = bundle()
                    sampleInputInfo = inputInfo[sampleName]
                    for dataTag in sampleInputInfo:
                        laneDataDir = os.path.join(fastqDir,sampleName,dataTag)
                        if os.path.exists(laneDataDir):
                            shutil.rmtree(laneDataDir)
                        impl.mkdir(laneDataDir)
                        tmpInputInfo[sampleName][dataTag] = laneDataDir
                        fq1 = sampleInputInfo[dataTag]['fq1']
                        fqname = os.path.basename(fq1)
                        dstFq = os.path.join(laneDataDir,fqname)
                        os.symlink(fq1, dstFq)

                        if not self.sample[sampleName].isSE:
                            fq2 = sampleInputInfo[dataTag]['fq2']
                            fqname = os.path.basename(fq2)
                            dstFq = os.path.join(laneDataDir,fqname)
                            os.symlink(fq2, dstFq)

                inputInfo = tmpInputInfo
            sampleName = self.option.multiSampleName
            hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'BWA_output')
            scriptsdir = impl.mkdir(self.option.workdir,"scripts",'gaea',sampleName)
            samplelist = self.results['init']['output'][sampleName]
            sampleInputInfo = inputInfo[sampleName]
            JobParam = []

            if self.ref.gender_mode == "both" and self.option.mode != 5:
                if self.info.female_counter > 0:
                    hadoopParam = ' -D mapred.job.name="bwa_%s_female" %s' % (subfunc,hadoop_param)
                    output = os.path.join(hdfs_outputPath,'female')
                    JobParam.append({
                        "INPUT": sampleInputInfo.female,
                        "OUTPUT": output,
                        "SUBFUNC":subfunc,
                        "SAMPLELIST": "%s %s" %(samplelistparam,samplelist.female),
                        "INDEX":self.ref.female.ref,
                        "HADOOPPARAM" : hadoopParam,
                        "OPTIONPARAM":self.alignment.parameter
                    })

                if self.info.male_counter > 0:
                    hadoopParam = ' -D mapred.job.name="bwa_%s_male" %s' % (subfunc,hadoop_param)
                    output = os.path.join(hdfs_outputPath,'male')
                    JobParam.append({
                        "INPUT": sampleInputInfo.male,
                        "OUTPUT": output,
                        "SUBFUNC":subfunc,
                        "SAMPLELIST": "%s %s" %(samplelistparam,samplelist.male),
                        "INDEX":self.ref.male.ref,
                        "HADOOPPARAM" : hadoopParam,
                        "OPTIONPARAM": self.alignment.parameter
                    })
            elif self.ref.gender_mode == "normal" or self.option.mode == 5:
                hadoopParam = ' -D mapred.job.name="bwa_%s" %s' % (subfunc,hadoop_param)
                output = hdfs_outputPath
                if self.option.mode == 5:
                    hadoopParam = ' -D multiSampleList="file://%s" %s' % (samplelist.normal,hadoopParam)
                JobParam.append({
                    "INPUT": sampleInputInfo.normal,
                    "OUTPUT": hdfs_outputPath,
                    "SUBFUNC":subfunc,
                    "SAMPLELIST": "%s %s" %(samplelistparam,samplelist.normal),
                    "INDEX":self.ref.normal.ref,
                    "HADOOPPARAM" : hadoopParam,
                    "OPTIONPARAM": self.alignment.parameter
                })

            cmd = []
            cmd.append("%s ${OUTPUT}" % fs_cmd.delete)
            cmd.append('${PROGRAM} ${HADOOPPARAM} -input ${INPUT} -output ${OUTPUT} -mapper ${MAPPER} -reducer "%s ${SUBFUNC} ${SAMPLELIST} ${INDEX} ${OPTIONPARAM} -"' % self.alignment.program )
            cmd.append("%s ${OUTPUT}/_*\n" % fs_cmd.delete)

            scriptPath = \
                impl.write_shell(
                    name = 'alignment',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    JobParamList=JobParam,
                    paramDict=ParamDict)

            result.output[sampleName] = hdfs_outputPath
            result.script[sampleName] = scriptPath
        else:
            if dependList[0] == 'init':
                for sampleName in inputInfo:
                    tmpInputInfo[sampleName] = bundle()
                    sampleInputInfo = inputInfo[sampleName]
                    for dataTag in sampleInputInfo:
                        laneDataDir = os.path.join(fastqDir,sampleName,dataTag)
                        if os.path.exists(laneDataDir):
                            shutil.rmtree(laneDataDir)
                        impl.mkdir(laneDataDir)
                        tmpInputInfo[sampleName][dataTag] = 'file://' +laneDataDir
                        fq1 = sampleInputInfo[dataTag]['fq1']
                        fqname = os.path.basename(fq1)
                        dstFq = os.path.join(laneDataDir,fqname)
                        if os.path.exists(dstFq):
                            os.remove(dstFq)
                        os.symlink(fq1, dstFq)

                        if not self.sample[sampleName].isSE:
                            fq2 = sampleInputInfo[dataTag]['fq2']
                            fqname = os.path.basename(fq2)
                            dstFq = os.path.join(laneDataDir,fqname)
                            if os.path.exists(dstFq):
                                os.remove(dstFq)
                            os.symlink(fq2, dstFq)

                inputInfo = tmpInputInfo


            for sampleName in inputInfo:
                scriptsdir = os.path.join(self.gaeaScriptsDir,sampleName)
                hdfs_outputPath = os.path.join(self.option.dirHDFS,sampleName,'BWA_output')
                sampleInputInfo = inputInfo[sampleName]
                JobParam = []
                RedParam = []

                for dataTag in sampleInputInfo:
                    hdfs_outDir = os.path.join(hdfs_outputPath,sampleName+"-"+dataTag)
                    name = "%s-%s" % (sampleName,dataTag)

                    rg = self.sample[sampleName]['rg'][dataTag]
                    parameter = "%s '%s' %s " % (rg_param_tag,rg,self.alignment.parameter)
                    gender = self.sample[sampleName].gender
                    RedParam.append({
                        "DATATAG":dataTag,
                        "SUBFUNC": subfunc,
                        "INDEX": self.ref[gender].ref,
                        "OPTIONPARAM":parameter
                    })

                    JobParam.append({
                        "DATATAG":dataTag,
                        "INPUT": sampleInputInfo[dataTag],
                        "OUTDIR": hdfs_outDir,
                        "HADOOPPARAM" : ' -D mapred.job.name="bwa_%s_%s" %s' % (subfunc,name,hadoop_param),
                        "REDUCER": '"sh %s"' % os.path.join(scriptsdir,'bwa_reducer_%s.sh' % name)
                    })

                #write script (multi file)
                impl.write_file(
                    fileName = 'bwa_reducer_%s-${DATATAG}.sh' % sampleName,
                    scriptsdir = scriptsdir,
                    commands=["%s ${SUBFUNC} ${INDEX} ${OPTIONPARAM} -" % self.alignment.program],
                    JobParamList=RedParam)

                cmd = []
                cmd.append('echo "alignment %s-${DATATAG}"'% sampleName)
                cmd.append("%s ${OUTDIR}" % fs_cmd.delete )
                cmd.append("${PROGRAM} ${HADOOPPARAM} -input ${INPUT} -output ${OUTDIR} -mapper ${MAPPER} -reducer ${REDUCER}")
                #write_shell name: no ext .sh (just one file)
                scriptPath = \
                    impl.write_shell(
                        name = 'alignment',
                        scriptsdir = scriptsdir,
                        commands=cmd,
                        JobParamList=JobParam,
                        paramDict=ParamDict)

                result.output[sampleName] = hdfs_outputPath
                result.script[sampleName] = scriptPath

        #return
        return result
