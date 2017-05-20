import os
import re
from string import Template

from gaeautils import Logger
from gaeautils.bundle import bundle


def _makedirs(loc):                                                                     
    try:
        os.makedirs(loc)
    except OSError, e:
        if not os.path.isdir(loc):
            raise e

def _do_join_file_name(mustBeAbs, *args):
    p = os.path.join(*args)
    tailSlash = (p[-1] == os.sep) and os.sep or ''
    p = os.path.normpath(p)
    if mustBeAbs != os.path.isabs(p):
        raise RuntimeError('not %s path: %s' % \
            (mustBeAbs and 'an absolute' or 'a relative', p))
    _makedirs(p)
    return p + tailSlash

def _join_abs_file_name(*args):
    return _do_join_file_name(True, *args)

def _join_rel_file_name(*args):
    return _do_join_file_name(False, *args)

def _generate_template(List):
    if isinstance(List,list):
        cmdStr = ''
        for n,line in enumerate(List):
            if n < len(List) - 1:
                cmdStr += line + '\n'
            else:   
                cmdStr += line
        return Template(cmdStr)
    elif isinstance(List,str):
        return Template(List)
    else:
        return 0
        
def _script_append(fh, t, JobParamList=[], paramDict={}):
    if JobParamList:
        for d in JobParamList:
            if isinstance(d,list):
                _script_append(fh, t, d, paramDict)
            elif isinstance(d,dict):
                if paramDict:
                    d.update(paramDict)
                print >>fh, t.safe_substitute(d)
    else:      
        print >>fh, t.safe_substitute(paramDict)
        
    return 0


class parseApp(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.files = {}
        self.allocDirectories = []
        self.directories = set()
        self.steps = []
        self.services = []
        self.notifications = []
        self.log = Logger('log.txt','2','workflow',True).getlog()
    
    
    def delete_HDFS_dir(self, impl, hdfs_dir):
        cmdStr = "%s %s\n" % (impl.fs_cmd.exist, hdfs_dir)
        cmdStr += "if [ $? -ne 0 ]; then\n"
        cmdStr += "    %s %s\n" % (impl.fs_cmd.delete, hdfs_dir)
        cmdStr += "fi\n"
        return cmdStr
    
    def splitext(self, p):
        if not os.path.exists(p):
            return False
        else:
            return os.path.splitext(os.path.basename(p))
    
    def mkdir(self, *args):
        p = _join_abs_file_name(*args)
        self.directories.add(p)
        return p
    
    def mkfile(self, name, data):
        if not os.path.isabs(name):
            raise RuntimeError('not an absolute path: %s' % name)
        name = os.path.normpath(name)
        self.files[name] = data
        return name 
    
    def paramRectify(self,paramStr,paramElem,mustBe=True):
        if mustBe:
            if paramStr.find(paramElem) == -1:
                paramStr += " %s " % paramElem
        elif paramStr.find(paramElem) != -1:
                return paramStr.replace('-I', '')
        return paramStr
            
    def fileAppend(self,fh,commands,JobParamList={}):
        t = _generate_template(commands)
        for param in JobParamList:
            print >>fh, t.safe_substitute(param)
    
    def write_file(self,fileName,scriptsdir,commands,JobParamList=None,paramDict={},addShellHeader=False):
        scriptDict = bundle()
        scriptDict.script = []
        
        t = _generate_template(commands)
        m = re.match('.*\$\{(\S+)\}.*',fileName)
        
        if JobParamList and m:
            for d in JobParamList:
                if not d.has_key(m.group(1)):
                    self.log.error("Wrong about impl.write_file paramter: fileName. No %s in JobParamList." % m.group(1))
                if paramDict:
                    d.update(paramDict)
                file_name = _generate_template(fileName).safe_substitute(d)
                scriptFile = os.path.join(scriptsdir,file_name)
                scriptDict["script"].append(scriptFile)
                script = open(scriptFile, 'w')
                print >>script, t.safe_substitute(d)
        else:
            scriptFile = os.path.join(scriptsdir,fileName)
            scriptDict["script"].append(scriptFile)
            script = open(scriptFile, 'w')
            if addShellHeader:
                print >>script, '#!/bin/bash'
                print >>script, "echo ==========start %s at : `date` ==========" % os.path.splitext(fileName)[0] 
                _script_append(script, t, JobParamList, paramDict)
                print >>script, "echo ==========end %s at : `date` ========== " % os.path.splitext(fileName)[0] 
            else:   
                _script_append(script, t, JobParamList, paramDict)
            script.close()
        return scriptDict
        
    def write_shell(self, name, scriptsdir, commands, JobParamList=[], paramDict={}):
        scriptDict = bundle()
        t = _generate_template(commands)
        
        scriptFile = os.path.join(scriptsdir,name+'.sh')   
        script = open(scriptFile, 'w')
        print >>script, '#!/bin/bash'
        print >>script, "echo ==========start %s at : `date` ==========" % name
        _script_append(script, t, JobParamList, paramDict)
        print >>script, ""  
        print >>script, "echo ==========end %s at : `date` ========== " % name
        script.close()
        return scriptFile
    
    def write_scripts(self, name, commands, JobParamList=[], paramDict={}):
        scriptDict = bundle()
        t = _generate_template(commands)
        
        
        for d in JobParamList:
            scriptsdir = d.get('SCRDIR')
            sampleName = d.get('SAMPLE')
            
            if not scriptsdir or not sampleName:
                self.log.error("Error in step (%s) JobParamList(no SMAPLE or SCRDIR)." % name) 
                exit(1)
            
            if paramDict:
                d.update(paramDict)
                
            scriptDict[sampleName] = os.path.join(scriptsdir,name+'.sh')   
            script = open(scriptDict[sampleName], 'w')
            
            print >>script, '#!/bin/bash'
            print >>script, "echo ==========start %s at : `date` ==========" % name
            _script_append(script, t, paramDict=d)
            print >>script, ""  
            print >>script, "echo ==========end %s at : `date` ========== " % name
            script.close()
            
        return scriptDict
            
    def write_Scripts(self, name, scriptsdir, commands, JobParamList=[], paramDict={}, reducer=True):
        scriptDict = bundle()
        t = _generate_template(commands)
        
        scriptDict["script"] = []
        for n, d in enumerate(JobParamList):
            if paramDict:
                d.update(paramDict)
            dataTag = str(n)
            if d.get('DATATAG'):
                dataTag = d.get('DATATAG')
            scriptFile = os.path.join(scriptsdir,name+'_'+  dataTag  +'.sh')
            scriptDict["script"].append(scriptFile)
            script = open(scriptFile, 'w')
            if reducer:
                print >>script, t.safe_substitute(d)
            else:
                print >>script, '#!/bin/bash'
                print >>script, "echo ==========start %s at : `date` ========== %s" % name
                print >>script, t.safe_substitute(d)
    #                 print >>script, "\n"          
                print >>script, "echo ==========end %s at : `date` ========== %s" % name
            script.close()
                
        return scriptDict
                
