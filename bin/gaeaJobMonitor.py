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

    check_step = ['filter', 'alignment']
    if step in check_step:
        if mapN == 0 and reduceN == 0:
            return False
        
    return True

def run(args,state):
    analysisDict = state.analysisDict
    sampleName = args.sampleName
    logger = Logger(os.path.join(state.scriptsDir,'log'),'1','gaeaJobMonitor',False).getlog()
    isComplete = bundle()
    
    all_done = True    

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
        p = subprocess.Popen('sh %s' % script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        isComplete[step] = check_log(p,script,sampleName,n, step)
        if isComplete[step] or step == 'alignment':
            if step == 'alignment':
                isComplete[step] = True
            printtime("step: %s complete" % step)
            logger.info('%s - step %d: %s complete' % (sampleName, n, step))
            out_fh = open(script+'.o', 'w')
            for line in p.stdout.readlines():    
                print >>out_fh, line[:-1]
            p.wait()
        else:
            all_done = False    
            printtime("%s failed" % step)
            logger.warning('%s - step %d: %s failed' % (sampleName, n, step))
            if p.returncode == None:
                p.kill()
                
    return all_done
                #don't qdel 
#                 sys.exit(1)
#         elif args.jobList != None and os.path.exists(args.jobList):
#             sge = get_SGE_state(args.jobList)
#             if sge:
#                 jobId = sge[sampleName][step]
#                 hold_jid = ''
#                 for depstep in analysisDict.get(step).depend:
#                     if not isComplete[depStep]:
#                         isComplete[step] = False
#                         break
#                     if analysisDict.get(depstep).platform == 'HPC':
#                         hold_jid += sge[sampleName][depstep] + ','
#                         
#                 if isComplete.has_key(step) and isComplete[step] == False:
#                     subprocess.call('qdel %s' % str(jobId),shell=True)
#                     continue
#                 
#                 if not hold_jid:
#                     hold_jid = 0       
#                 subprocess.call('qalter -hold_jid %s %s' % (hold_jid,str(jobId)),shell=True)
                    
#         sys.stdout.flush()
#         sys.stderr.flush()
      # return all_done
        
def HDFSclean(sampleName,state,cleanList,steptag,size_threshold=10):
    cleanBoolean = True
    if state.option.multi:
        for sample in state.results[steptag].output:
            data = state.results[steptag].output[sample]
            if not os.path.exists(data):
                cleanBoolean = False
                print "No bam file..."
            elif os.path.getsize(data)/1024 < size_threshold:
                cleanBoolean = False
                print "No vcf file..."
    else:
        data = state.results[steptag].output[sampleName]
        if not os.path.exists(data):
            cleanBoolean = False
            print "No bam file..."
        elif os.path.getsize(data)/1024 < size_threshold:
            cleanBoolean = False
            print "No vcf file..."
    print "Done"
            
    if cleanBoolean:
        for step in cleanList:
            if not step in state.analysisList:
                continue
            inputInfo = state.results[step].output[sampleName]
            if isinstance(inputInfo, bundle):
                for path in inputInfo.values():
                    cmd = "%s %s" % (state.fs_cmd.delete,path)
                    subprocess.call(cmd,shell=True)
            elif isinstance(inputInfo, str):
                cmd = "%s %s" % (state.fs_cmd.delete,inputInfo)
                subprocess.call(cmd,shell=True)
                
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
        
        isclean = run(args,state)
        subprocess.call("%s %s" % (state.fs_cmd.delete, os.path.join(state.option.dirHDFS,args.sampleName,'tmp')),shell=True)
        
        #TODO user-define the clean dir
        if not state.option.unclean:
            if state.results.has_key('bamSort'):
                cleanList = ['filter','alignment','rmdup','realignment']
                isclean = HDFSclean(args.sampleName,state,cleanList,'bamSort',1024)
                if state.results.has_key('mergeVariant'):
                    cleanList = ['filter','alignment','rmdup','realignment','genotype']
                    isclean2 = HDFSclean(args.sampleName,state,cleanList,'mergeVariant')
                    if not isclean2:
                        isclean = False
            elif state.results.has_key('mergeVariant'):
                if state.results.has_key('mergeVariant'):
                    cleanList = ['filter','alignment','rmdup','realignment','genotype']
                    isclean = HDFSclean(args.sampleName,state,cleanList,'mergeVariant')

            if isclean:		    
                cmd = "%s %s/%s" % (state.fs_cmd.delete, state.option.dirHDFS, args.sampleName)
                #subprocess.call(cmd, shell=True)
        if isclean:
            with open(os.path.join(state.scriptsDir,'log'), 'a') as f:
                f.write("Done!")
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

