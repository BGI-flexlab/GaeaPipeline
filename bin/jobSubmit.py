#!/usr/bin/env python
'''
testArg -- shortdesc

testArg is a description

It defines classes_and_methods

@author:     huangzhibo

@copyright:  2016 organization_name. All rights reserved.

@license:    license

@contact:    huangzhibo@genomics.cn
@deffield    updated: Updated
'''
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import json
import os
import re
import subprocess
import sys

from gaeautils import printflush, printtime, writefail, deleteFile
from gaeautils.bundle import bundle
from gaeautils.parseConfig import ParseConfig


__all__ = []
__version__ = '0.1'
__date__ = '2016-03-14'
__updated__ = '2016-03-14'

def writeCheckShell(script,state,failFile,successFile):
        out = open(script,'w')
        print >>out, '#!/bin/bash'
        print >>out,'perl %s %s' % (state.init.check_log, state.logfile)
        print >>out, 'if [ $? == 0 ]\nthen'
        print >>out, '\techo "success" > %s' % successFile
        print >>out, 'else'
        print >>out, '\techo "failed" > %s' % failFile
        print >>out, 'fi'

def writeGaeaShell(gaeaShell,state,job,sampleName):
    out = open(gaeaShell, 'w')
    print >>out, "source %s/bin/activate" % state.GAEA_HOME
    print >>out, "gaeaJobMonitor.py \\"
    print >>out, " --state %s \\" % os.path.join(state.stateDir,'state.json')
    print >>out, " --jobs %s \\" % job
    print >>out, " --sampleName %s \\" % sampleName

def parseRerun(rerun, isFile = True):
    rerunInfo = []
    if not isFile:
        if rerun.option.multiSample:
            rerunInfo.append([rerun.option.multiSampleName,rerun.analysisList])
        else:
            for sample in rerun.sample.keys():
                rerunInfo.append([sample,rerun.analysisList])
    else :
        with open(rerun, 'r') as f:
            for line in f:
                line = line.strip()
                field = line.split('\t')
                rerunInfo.append([field[0],field[1]])
    return rerunInfo

    
def getJobList(analysisDict,analysisList):
    #elem: 'step1,step2,step3'
    jobList = []
    if len(analysisList) == 1:
        return analysisList
    
    start = 0
    for n,step in enumerate(analysisList):
        if n == 0:
            continue
        if analysisDict[step].platform == 'H' and analysisDict[step].depS:
            stepStr = ','.join(analysisList[start:n])
            jobList.append(stepStr)
            start = n
        if len(analysisList) - 1 == n:
            stepStr = ','.join(analysisList[start:n+1])
            jobList.append(stepStr)
    
    return jobList

# def check_out(p, script, sampleName, n, step):
def check_out(p, script):
#     print "Run %s %s" % (sampleName,step)
    out_fh = open(script+'.o', 'w')
    while 1:
        out_info = p.stdout.readline()
        line = out_info[:-1]
        printflush(line)
        print >>out_fh, line
        if subprocess.Popen.poll(p) != None and not out_info:   
            break
    err_fh = open(script+'.e', 'w')
    while 1:
        err_info = p.stderr.readline()
        line = err_info[:-1]
        printflush(line)
        print >>err_fh, line
        if subprocess.Popen.poll(p) != None and not err_info:   
            break
        
#chech standalone step submit info
def check_out_sdn(p,failFile,is_at_TH=False):
    JobId = ''
    for line in p.stdout.readlines():
        printtime(line[:-1])
        if is_at_TH:
            jobInfo = re.match(r'^Submitted batch job (\d+)$', line)
        else:
            jobInfo = re.match(r'^Your job (\d+) \("(.*?)"\) has been submitted$', line)
        if jobInfo:
            JobId = jobInfo.group(1)
        else:
            writefail("err happened when submit (qsub/sbatch). ", failFile) 
    for line in p.stderr.readlines():
        printtime('ERROR: %s' % line[:-1])
    return JobId


def multi_run(args,state,rerunInfo):
    failFile = state.failFile
    analysisDict = state.analysisDict
    
    lastJobId = []
    
    sampleName = rerunInfo[0]
    jobList = getJobList(analysisDict,rerunInfo[1].split(','))
    
    for n,job in enumerate(jobList):
        if len(jobList) > 1: 
            shellName = 'gaea_%d' % n
        else:
            shellName = 'gaea'
            
        gaeaShell = os.path.join(state.gaeaScriptsDir,sampleName,'%s.sh'%shellName)
        writeGaeaShell(gaeaShell,state,job,sampleName)
        
        if args.type == 'local':
            p = subprocess.Popen('sh %s' % gaeaShell, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            check_out(p, gaeaShell)
            p.wait()
            stat = p.returncode
            if stat != 0:
                writefail('(gaea.sh) step failed with status %d' % stat, failFile) 
            
            for step in job.split(','):
                if analysisDict[step].platform == 'H':
                    continue
                
                lastJobId = []
                scriptsDict = state.results[step]['script']
                jobIdDict = bundle()
                
                depStep = []
                for deps in analysisDict[step].depend:
                    if analysisDict[deps].platform == 'S':
                        depStep.append(deps)
                        
                for sample_name in scriptsDict:
                    script = scriptsDict[sample_name]
                    sh_err = '%s.e' % script
                    sh_out = '%s.o' % script
                    
                    cmd = []
                    if state.hadoop.is_at_TH:
                        hold_jid = 'afterok'
                        for ds in depStep:
                            if state.results[ds].multiscript:
                                hold_jid = hold_jid + ':%s' % state.results[ds]['jobId'][state.option.multiSampleName]
                            elif state.results[step].multiscript:
                                for sample in state.results[ds].jobId:
                                    hold_jid =  hold_jid + ':%s' % state.results[ds].jobId[sample]
                            else:
                                hold_jid = hold_jid + ':%s' % state.results[ds]['jobId'][sample_name]
                        
                        if hold_jid == 'afterok':
                            cmd = ['sbatch','-p',args.partition,'-e',sh_err,'-o',sh_out, script]
                        else:
                            cmd = ['sbatch','-p',args.partition,'-d',hold_jid,'-e',sh_err,'-o',sh_out, script]
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        jobIdDict[sample_name] = check_out_sdn(p, failFile,True)
                    else:
                        hold_jid = ''
                        for ds in depStep:
                            if state.results[ds].multiscript:
                                hold_jid = hold_jid + '%s,' % state.results[ds]['jobId'][state.option.multiSampleName]
                            elif state.results[step].multiscript:
                                for sample in state.results[ds].jobId:
                                    hold_jid =  hold_jid + '%s,' % state.results[ds].jobId[sample]
                            else:
                                hold_jid = hold_jid + '%s,' % state.results[ds]['jobId'][sample_name]
                                
                        if state[step].get('mem'):
                            vf = 'vf=%s' % state[step].mem
                        if hold_jid:    
                            if args.partition:
                                cmd = ['qsub','-cwd','-l',vf,'-hold_jid',hold_jid,'-q',args.queue,'-P',args.partition,'-e',sh_err,'-o',sh_out, script]
                            else:
                                cmd = ['qsub','-cwd','-l',vf,'-hold_jid',hold_jid,'-q',args.queue,'-e',sh_err,'-o',sh_out, script]
                        else:
                            if args.partition:
                                cmd = ['qsub','-cwd','-l',vf,'-q',args.queue,'-P',args.partition,'-e',sh_err,'-o',sh_out, script]
                            else:
                                cmd = ['qsub','-cwd','-l',vf,'-q',args.queue,'-e',sh_err,'-o',sh_out, script]
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        jobIdDict[sample_name] = check_out_sdn(p, failFile)
                    lastJobId.append(jobIdDict[sample_name])
                state.results[step]['jobId'] = jobIdDict
                
                        
                
        elif args.type == 'submit':
            sh_err = '%s.e' % gaeaShell
            sh_out = '%s.o' % gaeaShell
            gaea_queue = 'gaea.q'
            gaea_partition = 'hadoop'
            if state.hadoop.cluster != 'cluster35':
                gaea_queue = args.queue
                gaea_partition = args.partition
            if gaea_partition:
                cmd = ['qsub','-cwd','-l','vf=2g','-q',gaea_queue,'-P',gaea_partition,'-e',sh_err,'-o',sh_out, gaeaShell]
            else:
                cmd = ['qsub','-cwd','-l','vf=2g','-q',gaea_queue,'-e',sh_err,'-o',sh_out, gaeaShell]
            hold_jid = ''
            if n > 0:
                for ds in analysisDict[job.split(',')[0]].depend:
                    if analysisDict[ds].platform == 'S':
                        for sampleName in state.results[ds].jobId:
                            hold_jid =  hold_jid + '%s,' % state.results[ds].jobId[sampleName]
                if hold_jid:
                    if gaea_partition:
                        cmd = ['qsub','-cwd','-l','vf=2g','-hold_jid',hold_jid,'-q',gaea_queue,'-P',gaea_partition,'-e',sh_err,'-o',sh_out, gaeaShell]
                    else:
                        cmd = ['qsub','-cwd','-l','vf=2g','-hold_jid',hold_jid,'-q',gaea_queue,'-e',sh_err,'-o',sh_out, gaeaShell]
            p = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for line in p.stderr.readlines():
                printtime('ERROR: (%s) %s' % (shellName,line[:-1]))
            for line in p.stdout.readlines():
                printtime(line[:-1])
                jobInfo = re.match(r'^Your job (\d+) \("(.*?)"\) has been submitted$', line)
                if jobInfo:
                    state.results.gaeaJobId = jobInfo.group(1)
                    lastJobId.append(jobInfo.group(1))
                else:
                    writefail("err happened when qsub. (%s) " % shellName, failFile)
                    exit(1) 
            p.wait()
            
            for step in job.split(','):
                if analysisDict[step].platform == 'H':
                    continue
                jobIdDict = bundle()
                scriptsDict = state.results[step]['script']
                
                depStep = []
                depHDP = False
                for deps in analysisDict[step].depend:
                    if analysisDict[deps].platform == 'S':
                        depStep.append(deps)
                    else:
                        depHDP = True
                        
                lastJobId = []
                for sample_name in scriptsDict:
                    script = scriptsDict[sample_name]
                    sh_err = '%s.e' % script
                    sh_out = '%s.o' % script
                    
                    
                    hold_jid = ''
                    for ds in depStep:
                        if state.results[ds].multiscript:
                            hold_jid = hold_jid + '%s,' % state.results[ds]['jobId'][state.option.multiSampleName]
                        elif state.results[step].multiscript:
                            for sample in state.results[ds].jobId:
                                hold_jid =  hold_jid + '%s,' % state.results[ds].jobId[sample]
                        else:
                            hold_jid = hold_jid + '%s,' % state.results[ds]['jobId'][sample_name]
                    if depHDP:
                        hold_jid = hold_jid + '%s,' % state.results.gaeaJobId
                    
                    vf = 'vf=5g'
                    if state[step].get('mem'):
                        vf = 'vf=%s' % state[step].mem
                    else:
                        printtime("Standalone Step %s: No set mem info for SGE. Default:'5G'. " % step)
                        
                    if hold_jid:    
                        if args.partition:
                            cmd = ['qsub','-cwd','-l',vf,'-hold_jid',hold_jid,'-q',args.queue,'-P',args.partition,'-e',sh_err,'-o',sh_out, script]
                        else:
                            cmd = ['qsub','-cwd','-l',vf,'-hold_jid',hold_jid,'-q',args.queue,'-e',sh_err,'-o',sh_out, script]
                    else:
                        if args.partition:
                            cmd = ['qsub','-cwd','-l',vf,'-q',args.queue,'-P',args.partition,'-e',sh_err,'-o',sh_out, script]
                        else:
                            cmd = ['qsub','-cwd','-l',vf,'-q',args.queue,'-e',sh_err,'-o',sh_out, script]
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    jobIdDict[sample_name] = check_out_sdn(p, failFile)
                    lastJobId.append(jobIdDict[sample_name])
                    
                state.results[step]['jobId'] = jobIdDict    
                
    allLastJobId = ','.join(lastJobId)
    return allLastJobId         
    
    

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

  Created by huangzhibo on %s.
  Copyright 2016 BGI_bigData. All rights reserved.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-s", "--state", dest="state", help="state file,[default: %(default)s]",required=True)
        parser.add_argument("-r", "--rerun", dest="rerun", default='all',help="rerun file,[default: %(default)s]")
#         parser.add_argument("-s", "--submit", action="store_true", default=False, help="submit to SGE. if False , just generator gaea.sh. [default: %(default)s]")
        parser.add_argument("-t", "--type", dest="type", choices=['write','local','submit'], type=str, default="write", help="1.write: just write run scripts; 2.local: run tasks on one local node; 3:submit: submit tasks to SGE [default: %(default)s]")
        parser.add_argument("-q", "--queue", dest="queue", help="the queue of the job. [default: %(default)s]")
        parser.add_argument("-p", "--partition", dest="partition",  help="the job partition. [default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        # Process arguments
        args = parser.parse_args()
        if not os.path.exists(args.state):
            printtime('ERROR: (--state: %s) - No such file or directory' % args.state)
            return 2
        state = ParseConfig(args.state).parseState()
#         if state.init.has_key("GAEA_HOME"):
#             os.environ["GAEA_HOME"] = state.GAEA_HOME
#             os.environ["PATH"] = os.environ["GAEA_HOME"] + ':' + os.environ["PATH"]

        state.failFile = os.path.join(state.stateDir,"failed")
        state.successFile = os.path.join(state.stateDir,"success")
        deleteFile(state.failFile)
        deleteFile(state.successFile)
        
        if os.path.exists(state.logfile):
            if not os.path.exists('%s.backup' % state.logfile):
                os.rename(state.logfile,'%s.backup' % state.logfile)
            else:
                subprocess.call("cat %s >>%s.backup" % (state.logfile,state.logfile),shell=True)
                deleteFile(state.logfile)
                
        if args.rerun == 'all':
            rerunInfo = parseRerun(state,False)
        elif args.rerun:
            rerunInfo = parseRerun(args.rerun)
            if not rerunInfo:
                rerunInfo = parseRerun(state,False)
                
        if args.type == 'submit' and state.hadoop.is_at_TH:
            args.type = 'local'
         
        state.hasSDNstep = False 
        for l in rerunInfo:
            for s in l[1].split(','):
                if state.analysisDict[s].platform == 'S':
                    state.hasSDNstep = True
                    
        if state.hasSDNstep:
            if args.type == 'local' and not state.hadoop.is_at_TH:
                writefail("Has standalone step, please submit tasks to SGE. (-t submit)",state.failFile) 
                
            if not state.hadoop.is_at_TH:
                if not args.queue: # or not args.partition:
                    writefail("Has standalone step, please set parameters: -q -P ",state.failFile) 
                    
        lastJobId = multi_run(args,state,rerunInfo[0])
            
            
        json.dump(state.results, open('%s/results.json' % state.stateDir, 'w'),indent=4)
        
        if args.type == 'submit':
            script = os.path.join(state.gaeaScriptsDir,"check_complete.sh")
            writeCheckShell(script,state,state.failFile,state.successFile)
            sh_err = '%s.e' % script
            sh_out = '%s.o' % script
            
            hold_jid = ''
            printtime("check end (%s) " %lastJobId)
            if re.match("\d+", lastJobId):
                hold_jid = lastJobId
            
            cmd = []
            if hold_jid:
                if state.hasSDNstep:
                    if args.partition:
                        cmd = ['qsub','-cwd','-l','vf=0.5g', '-hold_jid',hold_jid,'-q',args.queue,'-P',args.partition,'-e',sh_err,'-o',sh_out, script]
                    else:
                        cmd = ['qsub','-cwd','-l','vf=0.5g', '-hold_jid',hold_jid,'-q',args.queue,'-e',sh_err,'-o',sh_out, script]
                else:
                    cmd = ['qsub','-cwd','-l','vf=0.5g', '-hold_jid',hold_jid,'-q','gaea.q','-P','hadoop','-e',sh_err,'-o',sh_out, script]
            else:
                if state.hasSDNstep:
                    if args.partition:
                        cmd = ['qsub','-cwd','-l','vf=0.5g', '-q',args.queue,'-P',args.partition,'-e',sh_err,'-o',sh_out, script]
                    else:
                        cmd = ['qsub','-cwd','-l','vf=0.5g', '-q',args.queue,'-e',sh_err,'-o',sh_out, script]
                else:
                    cmd = ['qsub','-cwd','-l','vf=0.5g', '-q','gaea.q','-P','hadoop','-e',sh_err,'-o',sh_out, script]
            
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for line in p.stdout.readlines():
                printtime(line[:-1])
                jobInfo = re.match(r'^Your job (\d+) \("(.*?)"\) has been submitted$', line)
                if not jobInfo:
                    writefail("err happened when qsub. ", state.failFile) 
            for line in p.stderr.readlines():
                printtime('ERROR: (check_complete.sh) %s' % line[:-1])
            p.wait()
        elif args.type == 'local':       
            failed = False
            logFile = open(state.logfile,'r')
            if os.path.exists(state.logfile):
                logFile = open(state.logfile,'r')
                for line in logFile:
                    m = re.match('.*fail.*', line)
                    if m:
                        writefail("%s "% line, state.failFile) 
                        failed = True
            else:
                writefail("no start", state.failFile) 
                failed = True
            if not failed:
                stat = open(os.path.join(state.stateDir,'success'), 'w')
                print >> stat, 'success'
            stat.close()
            
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        with open(os.path.join(state.stateDir,'failed'), 'w') as f:
            f.write("Error in submit jobs!")
        
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    sys.exit(main())

