#!/usr/bin/env python
# encoding: utf-8
'''
Gaea.py--This program is used for generate Gaea workflow scripts.

@author:     huangzhibo

@copyright:  2016 BGI BigData. All rights reserved.

@contact:    huangzhibo@genomics.cn
@deffield    updated: Updated
'''

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from gaeautils import Logger, printtime, printflush, deleteFile, implapp, \
    search_mod
from gaeautils.bundle import bundle
from gaeautils.parseConfig import ParseConfig
from gaeautils.parseSampleList import ParseSampleList
import json
import os
import signal
import stat
import subprocess
import sys


__all__ = []
__version__ = '2.0.0 beta'
__date__ = '2016-01-14'
__updated__ = '2016-04-18'

DEBUG = 0
TESTRUN = 0
PROFILE = 0

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg
    
logger = Logger('log.txt','2','Gaea',True).getlog()
def createWorkflowObject(workflowClass, state):                                        
    wf = workflowClass(state)
    return wf

def writeRunShell(gaeaShell,state):
    out = open(gaeaShell, 'w')
    print >> out, '#!/bin/sh'
    print >>out, "source %s/bin/activate" % state.GAEA_HOME
    print >>out, 'runtype=$*'
    print >>out, 'Usage()\n{'
    print >>out, '\techo "Usage: ./run.sh <options>"'
    print >>out, '\techo "       Run Tasks (Local) : ./run.sh"'
    print >>out, '\techo "       Run Tasks ( SZ-SGE ) : ./run.sh submit"\n}'
    print >>out, 'if [ "$runtype" == "write" ] || [ "$runtype" == "w" ]; then'
    print >>out, '\truntype="write"'
    print >>out, 'elif [ "$runtype" == "submit" ] || [ "$runtype" == "s" ]; then'
    print >>out, '\truntype="submit"'
    print >>out, 'else'
    print >>out, '\truntype="local"'
    print >>out, '\techo "write gaea.sh..."'
    print >>out, 'fi'
    if state.option.multi:
        print >>out, "jobSubmit.py \\"
    else:
        print >>out, "jobSubmitS.py \\"
    print >>out, " --state %s \\" % os.path.join(state.stateDir,'state.json')
    print >>out, " --rerun %s \\" % os.path.join(state.stateDir,'rerun.list')
    if state.option.queue:
        print >>out, " --queue %s \\" % state.option.queue
    if state.option.partition:
        print >>out, " --partition %s \\" % state.option.partition
    print >>out, " --type ${runtype}"

impl = implapp.impl()

def run(args):
    os.environ['GAEA_HOME'] = os.path.split(os.path.realpath(__file__))[0]
    createVar = locals()
    defaultConfig = os.path.join(os.environ['GAEA_HOME'],'config','default.json')
    usercfg = bundle()
    try: 
        usercfg = ParseConfig(defaultConfig).parse(args.config)
    except Exception,e:  
        raise RuntimeError("Parse UserConfig failed," + repr(e) + "\n")
    
    usercfg.GAEA_HOME =  os.environ['GAEA_HOME']
    usercfg.scriptsDir = impl.mkdir(args.workdir,"scripts")
    usercfg.gaeaScriptsDir = impl.mkdir(usercfg.scriptsDir,'gaea')
    usercfg.stateDir = impl.mkdir(usercfg.scriptsDir,'state')
    usercfg.logfile = os.path.join(usercfg.scriptsDir,'log')
    deleteFile(usercfg.logfile)
    if usercfg.Path.get('appDir'):
        usercfg.Path.appDir = usercfg.Path.appDir + ":" +os.path.join(usercfg.GAEA_HOME,'workflow')
    else:
        usercfg.Path.appDir = os.path.join(usercfg.GAEA_HOME,'workflow')
    if usercfg.Path.get('modeDir'):
        usercfg.Path.modeDir = usercfg.Path.modeDir + ":" +os.path.join(usercfg.GAEA_HOME,'mode')
    else:
        usercfg.Path.modeDir = os.path.join(usercfg.GAEA_HOME,'mode')
        
    if usercfg.hadoop.fs_mode == 'file':
        args.dirHDFS = impl.mkdir(os.path.abspath(args.dirHDFS))
        os.chmod(args.dirHDFS, stat.S_IRWXU+stat.S_IRWXG+stat.S_IRWXO)
        usercfg.hadoop.input_format = 'file'
    
    results = bundle()
    
    #get APP class
    state = bundle()
    state.option = bundle()
    state.option.rupdate(args.__dict__, checkCompat=False)
    state.option.multiSampleName = "multi_sample"
    if state.option.multi:
        state.option.multiSample = True
    else:
        state.option.multiSample = False
    if usercfg.hasSDNstep:
        if usercfg.hadoop.is_at_TH:
            if not state.option.partition:
                state.option.partition = 'bgi_gd'
        elif not state.option.queue:  #or not state.option.partition:
                raise RuntimeError("Has Standalone step, please set parameters: -q -p for SGE")
        
    sampleInfo = bundle()
    try: 
        #sampleInfo = samplelistParser.parse(args.sampleList,state,args.mode)
        sampleInfo = ParseSampleList(args.sampleList, usercfg).parse(int(args.mode))
    except Exception,e:  
        raise RuntimeError("ParseSampleList:" + repr(e) + "\n")
        
        
    #get INIT default param   
    init_class = getattr(search_mod('init',usercfg.Path.appDir), "init")
    if hasattr(init_class, 'INIT'):
        state.rupdate(init_class.INIT, checkCompat=True, keyPath=init_class.__name__+'.INIT')
    self_defined_step = []
    for stepList in usercfg.analysis_flow:
        modname = stepList[1]
        if usercfg.self_defined.has_key(stepList[1]):
            modname = 'self_defined'
            self_defined_step.append(stepList[1])
            
        version = usercfg[modname].version if modname in usercfg and 'version' in usercfg[modname] else ''
        try:
            mod = search_mod(stepList[0]+'_'+modname, usercfg.Path.appDir, version)
        except Exception,e: 
            raise RuntimeError("search mod failed, please check your APP's Class name and INIT. %s " % e)
            
        if mod == -1:
            raise RuntimeError("Cann't find the module %s in analysis flow!" % (stepList[0]+'_'+modname+'.py'))
        createVar[stepList[1]] = getattr(mod,modname)
        
        #TODO 添加默认参数 usercfg
        klass = locals()[stepList[1]]
        if hasattr(klass, 'INIT'):
            state.rupdate(klass.INIT, checkCompat=True, keyPath=klass.__name__+'.INIT')
     
    state.rupdate(usercfg, checkCompat=False)
    
    
    #generate scripts        
    state.results = bundle()
    try:
        wf = createWorkflowObject(init_class, state)
        init_run = getattr(wf, "run")
        state.results['init'] = init_run(impl,sampleInfo)
    except Exception, e: 
        raise RuntimeError("init.py" + ": " + repr(e) + "\n")
        
    
    for step in state.analysisList:
        if step == 'init':
            continue
        wf = createWorkflowObject(locals()[step], state)
        method = getattr(wf, "run")
        dependList = state.analysisDict[step]['depend']
        try:
            if step in self_defined_step:
                state[step]=bundle()
                if state.self_defined[step].get('mem'):
                    state[step]['mem'] =state.self_defined[step].mem
                else:
                    state[step]['mem'] = '5G'
                    
                state.results[step] = method(impl,dependList,step)
            else:
                state.results[step] = method(impl,dependList)
        except Exception, e:  
            raise RuntimeError(step+".py" + ": " + repr(e) + "\n")
            
#     json.dump(state, open('%s/state.json' % usercfg.stateDir, 'w'),indent=4)
    #write rerun.list
    with open('%s/rerun.list' % usercfg.stateDir, 'w') as rerun_fh:
        if not state.option.multi:
            multi_step = []
            for step in state.analysisList:
                if state.results[step].script.has_key(state.option.multiSampleName):
                    ind = state.analysisList.index(step)
                    for s in state.analysisList[ind+1:]:
                        if step in state.analysisDict[s].depend:
                            raise RuntimeError("single step(%s) depend the multi (endtype) step(%s)" %(s,step))
                    state.analysisList.remove(step)
                    multi_step.append(step)
                    state.results[step].multiscript = True
                else:
                    state.results[step].multiscript = False
            jobs = ','.join(state.analysisList)
            for sampleName in sampleInfo.keys():
                rerun_fh.write('%s\t%s\n' % (sampleName,jobs))
            if multi_step:
                rerun_fh.write('%s\t%s\n' % (state.option.multiSampleName,','.join(multi_step)))
        else:
            if state.analysisList[0] == 'init':
                state.analysisList = state.analysisList[1:]
            jobs = ','.join(state.analysisList)
            rerun_fh.write('%s\t%s\n' % (state.option.multiSampleName,jobs))
    
    json.dump(state, open('%s/state.json' % usercfg.stateDir, 'w'),indent=4)
    sys.stdout.flush()
    sys.stderr.flush()
    
    #write run.sh
    runShell = os.path.join(usercfg.scriptsDir,'run.sh')
    writeRunShell(runShell,state)
    os.chmod(runShell, stat.S_IRWXU+stat.S_IRGRP+stat.S_IXGRP+stat.S_IROTH+stat.S_IXOTH)
    printtime("\nPlease run scripts/run.sh to submit tasks.")
    subprocess.call("sh %s write" % runShell,shell=True)

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
  Copyright 2016 BGI bigData. All rights reserved.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-w", "--workdir", dest="workdir", default=os.getcwd(),help="working directory of the workflow. [default: '.']" )
        parser.add_argument("-d", "--dirHDFS", dest="dirHDFS", help="hdfs work directory(When you use it in TH-1A,you must set it according lustre directory structure)",required=True)
        parser.add_argument("-s", "--sample", dest="sampleList", help="fq list or bam list or independent data list.",required=True)
        parser.add_argument("-m", "--mode", dest="mode", type=int, default=1, help="samplelist mode:1,standard BGI data;2,independent raw data;3,bam data; 4,vcf data. [default: %(default)s]")
        parser.add_argument("-c", "--config", dest="config", help="user config file.",required=True)
        parser.add_argument("-j", "--projectId", dest="projectId", help="Creat a dir in workdir as workdir")
        parser.add_argument("-n", "--multi", action="store_true", default = False,help="multi-sample in one run. [default: %(default)s]")
        parser.add_argument("-q", "--queue", dest="queue", help="the queue of the job. [default: %(default)s]")
        parser.add_argument("-p", "--partition", dest="partition",  help="the job partition. [default: %(default)s]")
        parser.add_argument("-t", "--type", dest="type", choices=['write','local','submit'], type=str, default="write", help="1.write: just write run scripts; 2.local: run tasks on one local node; 3:submit: submit tasks to SGE [default: %(default)s]")
        parser.add_argument("-u", "--unclean", action="store_true", help="Don't clean intermediate data,[default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        # Process arguments
        args = parser.parse_args()

        if not os.path.exists(os.path.abspath(args.sampleList)):
            raise RuntimeError("%s: No such file or directory." % args.sampleList)

        if not os.path.exists(os.path.abspath(args.config)):
            raise RuntimeError("%s: No such file or directory." % args.config)

        args.workdir = os.path.abspath(args.workdir)
        args.sampleList = os.path.abspath(args.sampleList)
        if not args.dirHDFS.startswith('/user'):
            args.dirHDFS = "/user{}".format(args.dirHDFS)

        if args.projectId:
            args.workdir = os.path.join(args.workdir, args.projectId)
            args.dirHDFS = os.path.join(args.dirHDFS, args.projectId)

        run(args)


        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        if DEBUG or TESTRUN:
            raise(e)
        
        statedir = impl.mkdir(args.workdir,'scripts','state')
        with open(os.path.join(statedir,'failed'), 'w') as f:
            f.write('generate scripts failed. please check your sample mode!')
            
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

def wfc_signal_handler(signum, frame):
    print 'Signal handler called with signal', signum
    raise RuntimeError('Signal handler called with signal '+str(signum))

if __name__ == "__main__":
    signal.signal(signal.SIGSEGV, wfc_signal_handler)
    signal.signal(signal.SIGILL, wfc_signal_handler)
    signal.signal(signal.SIGFPE, wfc_signal_handler)
    if DEBUG:
        sys.argv.append("-h")
        sys.argv.append("-r")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'testArg_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())
