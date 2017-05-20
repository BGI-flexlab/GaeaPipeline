#!/usr/local/bin/python2.7
# encoding: utf-8
import imp
import inspect
import json
import os, logging
import sys
import time

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


format_dict = {
   1 : logging.Formatter('[%(levelname)-7s]  %(message)s.'),
   2 : logging.Formatter('[%(levelname)-7s]  (%(filename)-15s line:%(lineno)d) %(message)s.'),
   3 : logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - (%(filename)s line:%(lineno)d) - %(message)s')
}

class Logger(object):
    def __init__(self, logname, loglevel, logger, console = True):
        '''
           指定保存日志的文件路径，日志级别，以及调用文件
           将日志存入到指定的文件中
        '''

        # 创建一个logger
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)

        # 定义handler的输出格式
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = format_dict[int(loglevel)]

        # 再创建一个handler，用于输出到控制台
        ch = logging.StreamHandler()
        if console:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.ERROR)
            # 创建一个handler，用于写入日志文件
            fh = logging.FileHandler(logname)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            

        ch.setFormatter(formatter)

        # 给logger添加handler
        self.logger.addHandler(ch)

    
    def getlog(self):
        return self.logger
    
def deleteFile(p):
    if os.path.exists(p):
        os.remove(p)
    
def printtime(message, *args):
    if args:
        message = message % args
    print "[ " + time.strftime('%X') + " ] " + message
    sys.stdout.flush()
    sys.stderr.flush()
    
def writefail(message, failFile):
    print "[ " + time.strftime('%X') + " ] " + 'ERROR: ' +message
    fail = open(failFile,'w') 
    print >>fail,message
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(3)
    
def writeToFile(message, filePath):
    fh = open(filePath,'w') 
    print >>fh,message
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(3)
    
def printflush(message, *args):
    if args:
        message = message % args
    print message
    sys.stdout.flush()
    sys.stderr.flush()

def wraplist(var, varname, etype=str):
    if isinstance(var, etype):
        return [var]
    elif isinstance(var, list):
        bads = [x for x in var if not isinstance(x, etype)]
        if not bads:
            return var
    else:
        bads = [var]
    raise TypeError('%s: expected %s or list of %s, found %s' %
                    (varname, etype.__name__, etype.__name__, type(bads[0]).__name__) )
    
def jsondump(obj, filename):
    f = open(filename, 'w')
    try:
        json.dump(obj, f, indent=2)
        print >>f, ''
    finally:
        f.close()

def makedirs(loc):                                                                     
    try:
        os.makedirs(loc)
    except OSError, e:
        if not os.path.isdir(loc):
            raise e
        
def writePidFile(fn):
    f = open(fn, 'w')
    print >>f, os.getpid()
    f.close()
    
def clean(x):
    if isinstance(x, dict):
        xx = bundle()
        for k, v in x.iteritems():
            kk = clean(k)
            vv = clean(v)
            xx[kk] = vv
        return xx
    elif isinstance(x, list):
        xx = []
        for k in x:
            kk = clean(k)
            xx.append(kk)
        return xx
    elif isinstance(x, unicode):
        return str(x)
    else:
        return x

def loadModule(codePath):
    assert codePath
    try:
        codeDir = os.path.dirname(codePath)
        codeFile = os.path.basename(codePath)
        moduleName,_ = os.path.splitext(codeFile)
        sys.path.append(codeDir)
        try:
            fin = open(codePath, 'r')
        except IOError,e:
            raise RuntimeError('cannot load module "%s": %s' % (codePath, str(e)))
        return  imp.load_source(moduleName, codePath, fin)
    finally:
        try: fin.close()
        except: pass

def search_mod(module_name, modDir, version=''):
    dir_list = modDir.split(":")
    if version:
        module_name = "{}-{}".format(module_name,version)
    for d in dir_list:
        code_path = os.path.join(d, module_name + ".py")
        if os.path.exists(code_path):
            return loadModule(code_path)
    return -1
