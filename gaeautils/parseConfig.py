#!/usr/local/bin/python2.7
# encoding: utf-8
'''
Created on 2016年1月18日

@author: huangzhibo
'''
from gaeautils import  Logger, clean
from gaeautils.bundle import bundle
import json
import os
from configobj import ConfigObj

logger = Logger('log.txt','2',"parseConfig",True).getlog()

def bundle_rcopy(cfg):
    newdict = bundle()
    for entry in cfg:
        this_entry = cfg[entry]
        if isinstance(this_entry, dict):
            this_entry = bundle_rcopy(this_entry)
        elif isinstance(this_entry, list): # create a copy rather than a reference
            this_entry = list(this_entry)
        elif isinstance(this_entry, tuple): # create a copy rather than a reference
            this_entry = tuple(this_entry)
        newdict[entry] = this_entry
    
    return newdict

def getAnalysisDict(analysis_flow):
    graph = bundle(init=bundle())
    graph['init']['depend'] = []
    graph['init']['platform'] = 'H'
    for stepList in  analysis_flow:
        if not graph.has_key(stepList[1]):
            graph[stepList[1]] = bundle()
        
        graph[stepList[1]]['depS'] = False
        if len(stepList) == 2:
            graph[stepList[1]]['depend'] = ['init']
            graph[stepList[1]]['platform'] = stepList[0].upper()
        else:
            graph[stepList[1]]['depend'] = stepList[2].split(',')
            graph[stepList[1]]['platform'] = stepList[0].upper()
            for dep in graph[stepList[1]]['depend']:
                if graph[dep]['platform'].upper() == 'S':
                    graph[stepList[1]]['depS'] = True
                    
    return graph

def getAnalysisList(analysis_flow):
    graph = bundle()
    oneStart = False
    for stepList in  analysis_flow:
        if not graph.has_key(stepList[1]):
            graph[stepList[1]] = []
            
        if len(stepList) == 2:
            if not oneStart:
                oneStart = True
                graph['init'] = [stepList[1]]
            else:
                raise RuntimeError('Error in analysis_flow: Multiple entry！(step named %s)' % stepList[1])
        else:
            dependList = stepList[2].split(',')
            for d in dependList:
                if not graph.has_key(d):
                    graph[d] = []
                graph[d].append(stepList[1])
    
    is_visit = dict( ( node, False ) for node in graph )
    li = []

    def dfs( graph, start_node ):
        
        for end_node in graph[start_node]:
            if not is_visit[end_node]:
                is_visit[end_node] = True
                dfs( graph, end_node )
        li.append( start_node )
        
    is_visit['init'] = True
    dfs( graph, 'init' )
    
    for start_node in graph:
        if not is_visit[start_node]:
            raise RuntimeError('step named %s does not exist' % start_node)
#             logger.error("config property (analysis_flow) format is wrong: step %s！"% start_node)
#             is_visit[start_node] = True
#             dfs( graph, start_node )

    li.reverse()
    return li

def check_ref_type(ref):
    if not ref.has_key('normal'):
        ref.normal = bundle()
    if not ref.has_key('male'):
        ref.male = bundle()
    if not ref.has_key('female'):
        ref.female = bundle()
    
    if ref.male.get('ref') and ref.female.get('ref'):
        logger.info('male.ref: %s, female:%s. use gender mode!' %(ref.male.ref,ref.female.ref) )
        ref['gender_mode'] = 'both'
        ref.normal.rupdate(ref.male)
            
    if ref.normal.get('ref') and ref.female.get('ref') and not ref.male.get('ref'):
#         logger.warning("male ref don't exists! use normal as male.")
        ref['gender_mode'] = 'both'
        ref.male.rupdate(ref.normal)
            
    if ref.normal.get('ref') and not ref.female.get('ref') and not ref.male.get('ref'):
#         logger.warning("male and female ref don't exists! use normal mode!")
        ref['gender_mode'] = 'normal'

class ParseConfig(object):
    '''
    This class is used to parse config file
    '''
    config = ''

    def __init__(self, config):
        '''
        Constructor
        '''
        self.config = config
        
    
    
    def findRef(self, refName):
        if os.path.exists(refName):
            refPath = refName
        elif os.path.exists(refName + ".fa"):
            refPath = refName + ".fa"
        elif os.path.exists(os.path.join(self.ref.defaultRefDir, refName + ".fa")):
            refPath = os.path.join(self.ref.defaultRefDir, refName + ".fa")
        else:
            logger.error("[ERROR] Can not find Reference: %s" % refName)
        logger.log.info("Use reference: %s" % refPath)
        return refPath
    
    def extendcfg(self,cfg):
        extendcfg = os.path.join(os.environ['GAEA_HOME'],'config','extend.cfg')
        excfg = ConfigObj(extendcfg)
        if cfg['hadoop'].get('cluster'):
            cluster = cfg['hadoop']['cluster']
            if excfg['hadoop'].has_key(cluster):
                excfg['hadoop'][cluster].update(cfg['hadoop'])
                cfg['hadoop'] = excfg['hadoop'][cluster]
            else:
                logger.error("[ERROR] Can not find this cluster: %s" % cluster)
                exit(2)
        if 'normal' in cfg['ref'] and 'ref' in cfg['ref']['normal']:
            value = cfg['ref']['normal']['ref']
            if value:
                if not os.path.exists(value):
                    if excfg['ref']['normal'].has_key(value) and excfg['ref']['normal'][value].has_key('ref'):
                        for key in excfg['ref']['normal'][value]:
                            if not key in cfg['ref']['normal'] or not os.path.exists(cfg['ref']['normal'][key]):
                                cfg['ref']['normal'][key] = excfg['ref']['normal'][value][key]
                else:
                    if not 'gaeaIndex' in cfg['ref']['normal'] or not os.path.exists(cfg['ref']['normal']['gaeaIndex']):
                        gaeaindex = os.path.join(os.path.dirname(value), 'GaeaIndex', 'ref_bn.list')
                        if os.path.exists(gaeaindex):
                            cfg['ref']['normal']['gaeaIndex'] = gaeaindex
                        else:
                            logger.error("[ERROR] Can not find ref.normale.gaeaIndex!")
                            exit(2)
                                
        if 'male' in cfg['ref'] and 'ref' in cfg['ref']['male']:
            value = cfg['ref']['male']['ref']
            if value and not os.path.exists(value):
                if excfg['ref']['male'].has_key(value) and excfg['ref']['male'][value].has_key('ref'):
                    for key in cfg['ref']['male'][value]:
                        cfg['ref']['male'][key] = excfg['ref']['male'][value][key]
                            
        if 'female' in cfg['ref'] and 'ref' in cfg['ref']['female']:
            value = cfg['ref']['female']['ref']
            if value and not os.path.exists(value):
                if excfg['ref']['female'].has_key(value) and excfg['ref']['female'][value].has_key('ref'):
                    for key in cfg['ref']['female'][value]:
                        cfg['ref']['female'][key] = excfg['ref']['female'][value][key]

    def parse_usercfg(self,cfgfile):
        cfg = ConfigObj(cfgfile)
        self.extendcfg(cfg)
        cfg['analysis_flow'] = cfg['analysis_flow'].values()
        cfg_bundle = bundle(cfg.dict())
        return bundle_rcopy(cfg_bundle)
        
        
    def parse_userjson(self,jsonfile):
        userConf = bundle()
        with open(jsonfile, 'r') as uf:
            data = uf.read()
            try: 
                userConf = clean(json.loads(data))
                self.extendcfg(userConf)
            except Exception,e:  
                print Exception,"%s, "%self.config,e
        return bundle_rcopy(userConf)
                 
    def parse(self,user_config=''):
        configInfo = bundle()
        if user_config:
            if user_config.endswith('.json') or user_config.endswith('config.json'):
                configInfo = self.parse_userjson(user_config)
            else:
                try:
                    configInfo = self.parse_usercfg(user_config)
                except Exception,e:  
                    print Exception,"%s, "%user_config,e
        
        # f = open(self.config, 'r')
        # try: data = f.read()
        # finally: f.close()
        
        # try:
        #     configInfo = bundle(clean(json.loads(data)))
        # except Exception,e:
        #     print Exception,"%s, "%self.config,e
        # configInfo.rupdate(userConf)
        
        if not configInfo.has_key('Path'):
            configInfo.Path = bundle()
        if not configInfo.has_key('self_defined'):
            configInfo.self_defined = bundle()
        
        necessary_property = ( "analysis_flow", "hadoop", "file", "ref")
        
        for np in necessary_property:
            if not configInfo.has_key(np):
                logger.error("config property: %s is not set" % np)
                exit(2)
                
        if configInfo.hadoop.get('is_at_TH'):
            if isinstance(configInfo.hadoop.is_at_TH,str):
                if configInfo.hadoop.is_at_TH == 'true' or configInfo.hadoop.is_at_TH == 'True':
                    configInfo.hadoop.is_at_TH = True
                else:
                    configInfo.hadoop.is_at_TH = False
        
        if  configInfo.hadoop.has_key('root'):
            configInfo.hadoop.bin = os.path.join(configInfo.hadoop.root,'bin/hadoop')
            configInfo.hadoop.streamingJar = os.path.join(configInfo.hadoop.root,'contrib/streaming/hadoop-streaming-0.20.2-cdh3u6.jar')
        if not os.path.exists(configInfo.hadoop.bin):
            logger.error("hadoop path: %s is not exists" % configInfo.hadoop.bin)
        if not os.path.exists(configInfo.hadoop.streamingJar):
            logger.error("streamingJar path: %s is not exists" % configInfo.hadoop.streamingJar)
            
        analysis_flow = []
        analysisList = ['init']
        for n,l in enumerate(configInfo.analysis_flow):
            depstep = ''
            for step in  l[1].split('|'):
                if not depstep:
                    if len(l) == 2 and n == 0:
                        analysis_flow.append([l[0],step])
                        analysisList.append(step)
                    elif len(l) == 3:
                        analysis_flow.append([l[0],step,l[2]])
                        analysisList.append(step)
                    else:
                        logger.error("bad analysis_flow param, please check it")
                else:
                    analysis_flow.append([l[0],step,depstep]) 
                    analysisList.append(step)
                depstep = step
                
        configInfo.analysisList = analysisList
        configInfo.analysis_flow = analysis_flow
        
        check_ref_type(configInfo.ref)
        configInfo.analysisDAGsort = getAnalysisList(configInfo.analysis_flow)
        configInfo.analysisDict = getAnalysisDict(configInfo.analysis_flow)
        
        #confirm the file exists
        for step in configInfo.analysisList:
            if configInfo.has_key(step):
                for line in configInfo[step].values():
                    if not line:
                        continue
                    if isinstance(line, str) and line[0] == '/':
                        if not os.path.exists(line):
                            logger.error("File: %s is not exists" % line)
                        
        configInfo.hasSDNstep = False
        for s in configInfo.analysisList:
            if configInfo.analysisDict[s].platform == 'S':
                configInfo.hasSDNstep = True
                break
            
        return configInfo
        
    def parseStep(self,configInfo):
        if not configInfo:
            configInfo = self.parse()
            
    def parseState(self):
        f = open(self.config, 'r')
        state = bundle()
        try: 
            data = f.read()
            state = bundle(clean(json.loads(data)))
        except Exception,e:  
            print Exception,"%s, "%self.config,e
        finally: f.close()
        
        return state
