#!/usr/bin/env python
# encoding: utf-8
from gaeautils import bundle, Logger, search_mod
import os

logger = Logger('log.txt','2',"parseSampleList",True).getlog()
    
class ParseSampleList(object):
    '''
    This class is used to parse sample list
    '''
    
    config = bundle()
    

    def __init__(self, sampleList, config):
        '''
        Constructor
        '''
        self.sampleList = sampleList
        self.config = config
        
        
    def rectify_gender(self,gender):
        if gender == 'F' or gender == 'female':
            return 'female'
        else:
            return 'male'
        
    def check_gender(self,sampleinfo,sampleName):
        sampleGender = ''
        for dataTag in sampleinfo:
            if not sampleGender:
                if sampleinfo[dataTag].get('gender'):
                    sampleGender = sampleinfo[dataTag]['gender']
            elif sampleGender != sampleinfo[dataTag]['gender']:
                logger.error("gender in %s is different in each lane!" % sampleName)
        return sampleGender
            
    def sampleParser(self,modetype):
        modname = 'mode'+str(modetype)
        parse_sample = getattr(search_mod(modname,self.config.Path.modeDir), 'parse_sample')
        sampleInfo = parse_sample(self.sampleList)
        return sampleInfo
    
    def parse(self,mode):
        self.config.info = bundle()
        self.config.info.female_counter = 0
        self.config.info.male_counter = 0
        self.config.sample = bundle()
        
        total_number = 0
        male_total_number = 0
        female_total_number = 0
        fq_file_dict = bundle()
        
        sampleInfo = self.sampleParser(mode)
        if mode == 3 or mode == 4:
            self.config.sample = sampleInfo
            if self.config.analysisList[0] == 'init':
                self.config.analysisList = self.config.analysisList[1:]
                
            if mode == 3:
                unavailableStep = ['filter','alignment']
                for step in unavailableStep:
                    if step in self.config.analysisList:
                        logger.error("Cann't run this step (%s) in mode3" % step)
                        exit(0)
#                         printtime("WARNING: step %s is dropped in mode 3."% step)
#                         self.config.analysisList.remove(step)
            elif mode == 4:
                unavailableStep = ['filter','alignment','rmdup','realignment','baserecal','genotype','bamSort']
                for step in unavailableStep:
                    if step in self.config.analysisList:
                        logger.error("Cann't run this step (%s) in mode4" % step)
                        exit(0)
#                         printtime("WARNING: step %s is dropped in mode 4."% step)
#                         self.config.analysisList.remove(step)
        else:
            fastq_necessary_property = ("id", "fq1", "rg")
            for sampleName in sampleInfo:
                rg_id_dict = bundle()
                sampleIsSE = bundle()
                self.config.sample[sampleName] = bundle(rg=bundle())
                
                sampleGender = self.rectify_gender(self.check_gender(sampleInfo[sampleName],sampleName))
                if sampleGender:
                    if self.config.ref.gender_mode != 'normal':
                        self.config.sample[sampleName].gender = sampleGender
                        if sampleGender == 'male':
                            self.config.info.male_counter += 1
                        else:
                            self.config.info.female_counter += 1
                    else:
                        self.config.sample[sampleName].gender = 'normal'
                else:
                    self.config.sample[sampleName].gender = 'normal'
                    
                pool = ''    
                for dataTag in sampleInfo[sampleName]:
                    if not pool:
                        pool = sampleInfo[sampleName][dataTag].get('pool')
                    
                    if self.config.ref.gender_mode == 'both':
                        gender = self.rectify_gender(sampleInfo[sampleName][dataTag].get('gender'))
                        if gender == 'female':
                            sampleInfo[sampleName][dataTag]['id'] = female_total_number
                            female_total_number += 1
                        if gender == 'male':
                            sampleInfo[sampleName][dataTag]['id'] = male_total_number
                            male_total_number += 1
                    else:
                        sampleInfo[sampleName][dataTag]['id'] = total_number
                        total_number += 1
                        
                    self.config.sample[sampleName]['rg'][dataTag] = sampleInfo[sampleName][dataTag]['rg']
                    
                    #RG.ID 同一样本的RG.ID不能重复
                    rg_id = sampleInfo[sampleName][dataTag]['rg'].split('ID:')[1].split('\\t')[0]
                    if not rg_id_dict.has_key(rg_id):
                        rg_id_dict[rg_id] = True
                    else:
                        logger.error('The same RG.ID in the different data (%s) of %s' % (dataTag,sampleName))
                    
#                     if not sampleInfo[sampleName][dataTag].has_key('gender'):
#                         logger.error("No gender info in %s %s!" % (sampleName,dataTag))
                        
                    for prop in fastq_necessary_property:
                        if not sampleInfo[sampleName][dataTag].has_key(prop):
                            logger.error("fastq prperty: %s is not exists in the %s of %s. You must set it in your sample file." % (prop,dataTag,sampleName))
                            
                    if not os.path.exists(sampleInfo[sampleName][dataTag]['fq1']):
                        raise RuntimeError("%s don't exists!" % sampleInfo[sampleName][dataTag]['fq1'])
                    
                    if sampleInfo[sampleName][dataTag].get('fq2') and sampleInfo[sampleName][dataTag]['fq2'] != 'null':
                        if not os.path.exists(sampleInfo[sampleName][dataTag]['fq2']):
                            raise RuntimeError("%s don't exists!" % sampleInfo[sampleName][dataTag]['fq2'])
                        
                        #fq file
                        if not fq_file_dict.has_key(sampleInfo[sampleName][dataTag]['fq2']):
                            fq_file_dict[sampleInfo[sampleName][dataTag]['fq2']] = True
                        else:
                            raise RuntimeError("%s used more than once!" % sampleInfo[sampleName][dataTag]['fq1'])
                        
                        if sampleIsSE.has_key('isSE') and sampleIsSE['isSE'] == True:
                            logger.error("%s: Have an error abort the prperty:fq2 in your sample file." % sampleName)
                        sampleIsSE['isSE'] = False
                    else:
                        if sampleIsSE.has_key('isSE') and sampleIsSE['isSE'] == False:
                            logger.error("%s: Have an error abort the prperty:fq2 in your sample file." % sampleName)
                        sampleIsSE['isSE'] = True
                        
                        
                    #fq file
                    if not fq_file_dict.has_key(sampleInfo[sampleName][dataTag]['fq1']):
                        fq_file_dict[sampleInfo[sampleName][dataTag]['fq1']] = True
                    else:
                        raise RuntimeError("%s used more than once!" % sampleInfo[sampleName][dataTag]['fq1'])
                        
                        
                self.config.sample[sampleName].pool = pool
                self.config.init.isSE = sampleIsSE['isSE']
                self.config.sample[sampleName].isSE = sampleIsSE['isSE']
        return sampleInfo


        
    
        