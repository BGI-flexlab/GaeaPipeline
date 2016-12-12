#!/usr/bin/env python
'''
testArg -- shortdesc

testArg is a description

It defines classes_and_methods

@author:     huangzhibo

@copyright:  2016 BGI_bigData. All rights reserved.

@license:    license

@contact:    huangzhibo@genomics.cn
@deffield    updated: Updated
'''

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import os
import re
import subprocess
import sys

from gaeautils.bundle import bundle
from gaeautils.parseConfig import ParseConfig
from gaeautils import Logger, printtime
from __builtin__ import False

__all__ = []
__version__ = '0.1'
__date__ = '2016-03-14'
__updated__ = '2016-03-14'

def get_SGE_state(jobId):
    sge = bundle()
    f = open(jobId,'r')
    for line in f:
        line = line.strip()
        field = line.split('\t')
        if not sge.has_key(field[0]):
            sge[field[0]] = bundle()
        sge[field[0]][field[1]] = field[2]
    return sge

def parseRerun(rerun):
    rerunInfo = bundle()
    if isinstance(rerun,bundle):
        if rerun.option.multiSample:
            rerunInfo.multiSample = rerun.analysisList
        else:
            for sample in rerun.sample.key():
                rerunInfo[sample] = rerun.analysisList
    elif isinstance(rerun,str):
        f = open(rerun, 'r')
        try: data = f.read()
        finally: f.close()
        
        for line in data:
            field = line.split('\s+')
            rerunInfo[field[0]] = field[1].split(',')
        return rerunInfo
    else:
        raise RuntimeError('parseRerun error!')
    
def check_log(p, script, sampleName, n, step):
    err_fh = open(script+'.e', 'w')
    mapN = 0
    reduceN = 0
        
    while 1:
        err_info = p.stderr.readline()
        line = err_info[:-1]
        print >>err_fh, line
#         if re.match('.*Status\s+:\s+FAILED$',line):
#             return False
        if re.match('.*Job\s+failed.*',line):
            return False
        if re.match('.*Job not successful.*',line):
            return False
        m = re.search('map 0% reduce 0%',line)
        if m:
            if mapN > 0 and mapN != 100:
                return False
            if reduceN > 0 and reduceN != 100:
                return False
            
        s = re.search('map (\d+)% reduce (\d+)%',line)
        if s:
            mapN = int(s.group(1))
            reduceN = int(s.group(2))
            
        JobComplete = re.search('Job complete:',line)
        if JobComplete:
            if mapN > 0 and mapN != 100:
                return False
            if reduceN > 0 and reduceN != 100:
                return False
        if subprocess.Popen.poll(p) != None and not err_info:   
            break
        
        sys.stdout.flush()
        sys.stderr.flush()
        
    return True

def run(args,state):
    analysisDict = state.analysisDict
    sampleName = args.sampleName
    logger = Logger(os.path.join(state.scriptsDir,'log'),'1','gaeaJobMonitor',False).getlog()
    isComplete = bundle()
    
    if args.debug:
        print 'run_func_good'
    
    jobList = args.jobs.split(',')
    
    if jobList[0] == 'init':
        if not state.results['init'].get('script'):
            jobList = jobList[1:]
    
    for num,step in enumerate(jobList):
        if analysisDict[step].platform == 'S':
            continue


        n = state.analysisList.index(step)
        if state.analysisList[0] != 'init':
            n += 1

        script = state.results[step]['script'][sampleName]
        if num > 0:
            for depStep in analysisDict[step].depend:
                if not isComplete[depStep]:
                    isComplete[step] = False
                    break
        if isComplete.has_key(step) and isComplete[step] == False:
            logger.warning('%s - step %d: %s failed' % (sampleName, n, step))
            continue

        printtime('step: %s start...' % step)
        out_fh = open(script+'.o', 'w')
        p = subprocess.Popen('sh %s' % script, shell=True, stdout=out_fh, stderr=subprocess.PIPE)
        isComplete[step] = check_log(p,script,sampleName,n, step)
        if isComplete[step]:
            printtime("step: %s complete" % step)
            logger.info('%s - step %d: %s complete' % (sampleName, n, step))
            p.wait()
        else:
            printtime("%s failed" % step)
            logger.warning('%s - step %d: %s failed' % (sampleName, n, step))
            if p.returncode == None:
                p.kill()
        out_fh.close()

def HDFSclean(args,state,cleanList,steptag,size_threshold=10):
    cleanBoolean = True
    for sample in state.results[steptag].output:
        data = state.results[steptag].output[sample]
        if not os.path.exists(data):
            cleanBoolean = False
        elif os.path.getsize(data)/1024 < size_threshold:
            cleanBoolean = False
            
    if cleanBoolean:
        for step in cleanList:
            if not step in state.analysisList:
                continue
            inputInfo = state.results[step].output[args.sampleName]
            if isinstance(inputInfo, bundle):
                for path in inputInfo.values():
                    cmd = "%s %s" % (state.fs_cmd.delete,path)
                    subprocess.Popen(cmd,shell=True)
            elif isinstance(inputInfo, str):
                cmd = "%s %s" % (state.fs_cmd.delete,inputInfo)
                subprocess.Popen(cmd,shell=True)
                
    return cleanBoolean

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by user_name on %s.
  Copyright 2016 organization_name. All rights reserved.
  
USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-s", "--state", dest="state", help="state file,[default: %(default)s]")
        parser.add_argument("-n", "--sampleName", dest="sampleName", help="sampleName,[default: %(default)s]",required=True)
        parser.add_argument("-j", "--jobs", dest="jobs", help="step String,[default: %(default)s]",required=True)
        parser.add_argument("-u", "--unclean", action="store_true", help="Don't clean intermediate data,[default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument("--debug",  action="store_true", help="print debug info")

        # Process arguments
        args = parser.parse_args()
        state = ParseConfig(args.state).parseState()
        
        run(args,state)
        
        #TODO user-define the clean dir
        if not args.unclean:
            cleanedList = []
            if state.results.has_key('bamSort'):
                cleanList = ['filter','alignment','rmdup','realignment']
                HDFSclean(args,state,cleanList,'bamSort',1024)
                if state.results.has_key('mergeVariant'):
                    cleanList = ['baserecal','genotype']
                    HDFSclean(args,state,cleanList,'mergeVariant')
            else:
                cleanList = ['filter','alignment','rmdup','realignment','genotype']
                if state.results.has_key('mergeVariant'):
                    cleanedList.extend(['baserecal','genotype'])
                    HDFSclean(args,state,cleanList,'mergeVariant')
        
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    sys.exit(main())

