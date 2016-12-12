# encoding: utf-8
import os
import shutil
import subprocess

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow
import qualitySystem


class init(Workflow):
    """ init data, init data path """

    INIT = bundle(hadoop=bundle(),init=bundle())
    INIT.init.multiUploader = 'multi_uploader.pl'
    INIT.init.gzUploader = "GzUpload.jar"
    INIT.init.bgzip = 'bgzip'
    INIT.init.samtools = 'samtools'
    INIT.init.qualitySystem = ''
    INIT.init.check_log = '%s'%os.path.join(os.environ['GAEA_HOME'],'bin','check_log.pl')
    INIT.hadoop.ishadoop2 = False
    INIT.hadoop.is_at_TH = False
    INIT.hadoop.fs_mode = 'hdfs'
    INIT.hadoop.input_format = 'file'
    INIT.hadoop.mapper_num = '112'
    INIT.hadoop.reducer_num = '112'

    def check_qs(self,sampleInfo):
        for sample_name in sampleInfo:
            for dataTag in sampleInfo[sample_name]:
                fq =  sampleInfo[sample_name][dataTag]['fq1']      
		self.init.qualitySystem = qualitySystem.getQualitySystem(fq)
                if self.init.qualitySystem != '-1':
                    return self.init.qualitySystem 
                
        if self.init.qualitySystem == '-1':
            raise RuntimeError('qualitySystem is wrong, the value is -1')
                
    def run(self, impl, sampleInfo):
        mode = self.option.mode
        result = bundle(output=bundle())
        
        #extend program path
        self.init.multiUploader = self.expath('init.multiUploader')
        self.init.gzUploader = self.expath('init.gzUploader')
        self.init.check_log = self.expath('init.check_log')
        self.init.bgzip = self.expath('init.bgzip', False)
        self.init.samtools = self.expath('init.samtools', False)

        
        
        if mode == 1 or mode == 2 or mode == 5:
            if self.option.multiSample:
                sampleName = self.option.multiSampleName
                scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
                self.analysisList = self.analysisList[1:]
                output = bundle()
                
                line = ["${ID}\t${RG}\t${FQ1}\t${FQ2}\t${ADP1}\t${ADP2}"]
                if self.ref.gender_mode == 'both' and mode != 5:
                    output.female = os.path.join(scriptsdir,"femalesampleinfo.list")
                    output.male = os.path.join(scriptsdir,"malesampleinfo.list")
                    MSLF = open(output.female, 'w')
                    MSLM = open(output.male , 'w')
                    for sample_name in sampleInfo.keys():
                        sample = sampleInfo[sample_name]
                        LineParam = []
                        for dataTag in sampleInfo[sample_name].keys():
                                LineParam.append({
                                    "ID": sample[dataTag]['id'],
                                    "RG": sample[dataTag]['rg'],
                                    "FQ1": 'file://'+sample[dataTag]['fq1'],
                                    "FQ2": sample[dataTag].has_key('fq2') and 'file://'+ sample[dataTag]['fq2'] or 'null' ,
                                    "ADP1": sample[dataTag].has_key('adp1') and 'file://'+ sample[dataTag]['adp1'] or 'null',
                                    "ADP2": sample[dataTag].has_key('adp2') and 'file://'+ sample[dataTag]['adp2'] or 'null'
                                })
                    
                        gender =  self.sample[sample_name]["gender"]
                        impl.fileAppend(
                                fh = gender=='female' and MSLF or MSLM,
                                commands=line,
                                JobParamList=LineParam)
                else:
                    output.normal = os.path.join(scriptsdir,"sampleinfo.list")
                    MSL = open(output.normal , 'w')
                    for sample_name in sampleInfo.keys():
                        sample = sampleInfo[sample_name]
                        LineParam = []
                        for dataTag in sample.keys():
                            LineParam.append({
                                "ID": sample[dataTag]['id'],
                                "RG": sample[dataTag]['rg'],
                                "FQ1": 'file://'+sample[dataTag]['fq1'],
                                "FQ2": sample[dataTag].has_key('fq2') and 'file://'+ sample[dataTag]['fq2'] or 'null' ,
                                "ADP1": sample[dataTag].has_key('adp1') and 'file://'+ sample[dataTag]['adp1'] or 'null',
                                "ADP2": sample[dataTag].has_key('adp2') and 'file://'+ sample[dataTag]['adp2'] or 'null'
                            })
                    
                        impl.fileAppend(
                                fh = MSL,
                                commands=line,
                                JobParamList=LineParam)
                        
                result.output[sampleName] = output
            else:
                result.script = bundle()
                for sampleName in sampleInfo.keys():
                    scriptsdir = impl.mkdir(self.gaeaScriptsDir,sampleName)
                    hdfs_gz_tmp = os.path.join(self.option.dirHDFS,sampleName,'data','gz_tmp')
                    sample = sampleInfo[sampleName]
                    output = bundle()
                    DataParam = []
                    cmd = []
                    for dataTag in sample.keys():
                        rawData = impl.mkdir(self.option.workdir, 'fq', 'raw_data',sampleName)
                        laneData = os.path.join(rawData, dataTag)
                        cmd.append("mkdir -p -m 777 %s" % laneData)
                        output[dataTag] = bundle()
                        pathTup = impl.splitext(sample[dataTag]['fq1'])
                        if pathTup and pathTup[1] == '.gz':
                            DataParam.append({
                                "KEY": sample[dataTag]['fq1'],
                                "VALUE": os.path.join(laneData,pathTup[0])
                            })
                            output[dataTag]['fq1'] = os.path.join(laneData,pathTup[0])
                        else:
                            output[dataTag]['fq1'] = sample[dataTag]['fq1']
                            
                        if self.init.isSE == False:  
                            pathTup = impl.splitext(sample[dataTag]['fq2'])
                            if pathTup and pathTup[1] == '.gz':
                                DataParam.append({
                                    "KEY": sample[dataTag]['fq2'],
                                    "VALUE": os.path.join(laneData,pathTup[0])
                                })
                                output[dataTag]['fq2'] = os.path.join(laneData,pathTup[0])
                            else:
                                output[dataTag]['fq2'] = sample[dataTag]['fq2']
                                
                        if sample[dataTag].has_key('adp1'):
                            pathTup = impl.splitext(sample[dataTag]['adp1'])
                            if pathTup and pathTup[1] == '.gz':
                                DataParam.append({
                                    "KEY": sample[dataTag]['adp1'],
                                    "VALUE": os.path.join(laneData,pathTup[0])
                                })
                                output[dataTag]['adp1'] = os.path.join(laneData,pathTup[0])
                            else:
                                output[dataTag]['adp1'] = sample[dataTag]['adp1']
                                  
                        if sample[dataTag].has_key('adp2'):
                            pathTup = impl.splitext(sample[dataTag]['adp2'])
                            if pathTup and pathTup[1] == '.gz':
                                DataParam.append({
                                    "KEY": sample[dataTag]['adp2'],
                                    "VALUE": os.path.join(laneData,pathTup[0])
                                })
                                output[dataTag]['adp2'] = os.path.join(laneData,pathTup[0])
                            else:
                                output[dataTag]['adp2'] = sample[dataTag]['adp2']
    #                 print DataParam  
                    if DataParam:
                        impl.write_file(
                            fileName='data.list',
                            scriptsdir = scriptsdir,
                            commands=["${KEY}\t${VALUE}"],
                            JobParamList=DataParam)
                    
                        mapper = []
                        mapper.append("#!/usr/bin/perl -w")
                        mapper.append("use strict;\n")
                        mapper.append("while(<STDIN>)\n{")
                        mapper.append("\tchomp;\n\tmy @tmp = split(/\\t/);")
                        mapper.append("\tif(!-e $tmp[0])\n\t{")
                        mapper.append("\t\tprint \"$tmp[0] don't exist.\\n\";")
                        mapper.append("\t\texit 1;\n\t}")
                        mapper.append("\tsystem(\"gzip -cd $tmp[0] >$tmp[1]\");\n}")
                        impl.write_file(
                                fileName='upload_mapper.pl',
                                scriptsdir = scriptsdir,
                                commands=mapper)
                        
                        
                        hadoop_parameter = ' -D mapred.job.name="gzip input data" '
                        hadoop_parameter += ' -D mapred.map.tasks=%d ' % len(DataParam)
                        hadoop_parameter += ' -D mapred.reduce.tasks=0 '
                        ParamDict={
                            "PROGRAM": "%s jar %s" % (self.hadoop.bin, self.hadoop.streamingJar),
                            "MAPPER": os.path.join(scriptsdir,'upload_mapper.pl'),
                            "INPUT": 'file://' + os.path.join(scriptsdir,'data.list'),
                            "OUTPUT": hdfs_gz_tmp,
                            "HADOOPPARAM": hadoop_parameter
                        }
                
                        cmd.append('%s ${OUTPUT}' % self.fs_cmd.delete)
                        cmd.append('${PROGRAM} ${HADOOPPARAM} -input ${INPUT} -output ${OUTPUT} -mapper "perl ${MAPPER}"')
        
                        #write script
                        scriptPath = \
                        impl.write_shell(
                                name = 'init',
                                scriptsdir = scriptsdir,
                                commands=cmd,
                                paramDict=ParamDict)
                        result.script[sampleName] = scriptPath
                        
                    result.output[sampleName] = output
                    
            if self.init.qualitySystem == '':
                self.check_qs(sampleInfo)
                print "[INFO   ]  -- qualitySystem is %s (autocheck)--" % self.init.qualitySystem 
            else:
                print "[INFO   ]  -- qualitySystem is %s --" % self.init.qualitySystem 
                
                #self.init.qualitySystem = 0

        elif mode == 3 or mode == 4:
            sampleName = self.option.multiSampleName
            
            startStep = self.analysisList[0]
            fs_type = ''
            if self.analysisDict[startStep].platform == 'H':
                fs_type = 'file://'
                
            if self.option.multiSample:
                inputDir = os.path.join(self.option.workdir,'raw_data','bams')
                result.output[sampleName] = fs_type + inputDir
                    
                if os.path.exists(inputDir):
                    shutil.rmtree(inputDir)
                impl.mkdir(inputDir)
                
                for sample_name in sampleInfo.keys():
                    bam = os.path.basename(sampleInfo[sample_name])
                    ln_bam = os.path.join(inputDir,bam)
                    os.symlink(sampleInfo[sample_name], ln_bam)
            else:
                for sample_name in sampleInfo.keys():
                    result.output[sample_name] = fs_type + sampleInfo[sample_name]
            
        #return
        return result
            
                      
