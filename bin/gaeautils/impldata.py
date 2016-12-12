#!/usr/bin/python
import json
import os, logging, pickle, sys

from gaeautils import Abort, wraplist
from gaeautils.bundle import bundle


def _findstep(name, lst):
    for s in lst:
        if s.name == name:
            return s
    return None

def _do_join_file_name(mustBeAbs, *args):
    p = os.path.join(*args)
    tailSlash = (p[-1] == os.sep) and os.sep or ''
    p = os.path.normpath(p)
    if mustBeAbs != os.path.isabs(p):
        raise RuntimeError('not %s path: %s' % \
            (mustBeAbs and 'an absolute' or 'a relative', p))
    return p + tailSlash

def _join_abs_file_name(*args):
    return _do_join_file_name(True, *args)

def _join_rel_file_name(*args):
    return _do_join_file_name(False, *args)

def _override_params(param, paramOverrides):
    result = []
    overrides = set()
    for x in paramOverrides:
        if x[0] == param.name:
            overrides.add(x[1])
    for p in param.p:
        if not p[0] in overrides:
            result.append( (p[0], str(p[1])) )
    for x in paramOverrides:
        if x[0] != param.name:
            continue
        if x[2] is None:
            continue
        elif isinstance(x[2], list) or isinstance(x[2], tuple):
            for subx in x[2]:
                result.append( (x[1], str(subx)) )
        else:
            result.append((x[1], str(x[2])))
    return result

class StageImplData(object):
    def __init__(self, workflow):
        self.files = {}
        self.allocDirectories = []
        self.directories = set()
        self.steps = []
        self.services = []
        self.notifications = []
        self.log = logging.getLogger('cgi.workflow-callback')
        self.log.setLevel(logging.__dict__[os.getenv('CGI_LOG_LEVEL', 'INFO')])
        self.workflow = workflow

    def abort(self, msg, *args):
        raise Abort(msg % args)

    def notifyAaa(self, data):
        self.notifications.append(data)

    def mkdir(self, *args):
        p = _join_abs_file_name(*args)
        self.directories.add(p)
        return p

    def allocAndMkdir(self, *args):
        '''Like mkdir(), but allocates the directory storage from
        self.workDirList, and constructs a symlink to that
        storage. The path join of the inputs must be a path under
        workDir.'''
        p = _join_abs_file_name(*args)
        self.allocDirectories.append(p)
        return p

    def mkfile(self, name, data):
        if not os.path.isabs(name):
            raise RuntimeError('not an absolute path: %s' % name)
        name = os.path.normpath(name)
        self.files[name] = data
        return name

    def fn(self, *args):
        return _join_abs_file_name(*args)
    filename = fn

    def relfn(self, *args):
        return _join_rel_file_name(*args)

    def command(self, exe, *args):
        params = []
        for ps in args:
            if not isinstance(ps, bundle):
                raise TypeError('expected parameter sets following the executable name')
            params += _override_params(ps, self.workflow.paramOverrides)
        tokens = [ exe ]
        for p in params:
            if p[0] == '':
                tokens.append(p[1])
            elif p[1] == '':
                tokens.append('--%s' % p[0])
            else:
                tokens.append('--%s="%s"' % p)
        return ' \\\n'.join(tokens)

    def pycommand(self, func, *args, **kwargs):
        '''Creates the command to run the given python function, passing it the given arguments.

        The function (func) must be picklable by the python pickle
        package. Basically, this means it must be a global function
        within a module. The arguments must be JSON-serializable. The
        func is required to accept the arrayParamValues element for
        this task as its first argument (always a dictionary object),
        and any additional parameters must be passed to the pycommand
        function. For non-array steps, the arrayParamValues element is
        still passed, but is a dictionary with no keys.'''

        funcString = self._escapetriplequote(pickle.dumps(func))
        argBundle = bundle(args=args, kwargs=kwargs)
        argString = self._escapetriplequote(json.dumps(argBundle,indent=2))

        lines = [ '#! /usr/bin/env python',
                  'import sys',
                  'sys.path = %s' % str(sys.path),
                  'import os, pickle, sys, wfclib.jsonutil',
                  'from cgiutils import bundle',
                  'func = pickle.loads("""%s""")' % funcString,
                  'argBundle = wfclib.jsonutil.loads("""%s""")' % argString,
                  'apv = bundle()',
                  'apvKeys = os.getenv("CGI_ARRAY_PARAM_NAMES")',
                  'if apvKeys is not None:',
                  '  for key in apvKeys.split(":"):',
                  '    apv[key] = os.getenv(key)',
                  'func(apv, *argBundle.args, **argBundle.kwargs)',
                  ]
        script = '\n'.join(lines)

        return "python -u - <<'@CGI_PYCOMMAND_HERE_DOC_DELIM'\n%s\n@CGI_PYCOMMAND_HERE_DOC_DELIM" % script

    def _escapetriplequote(self, ss):
        # Escape to put into python """-delimited string.
        return ss.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')

    def service(self, name, serviceCommand, serviceData, concurrencyLimit=None, hog=False):
        if concurrencyLimit is None:
            concurrencyLimit = 1200
        self._checkname(name)
        self.services.append(bundle(name=name, serviceCommand=serviceCommand,
                                    serviceData=serviceData,
                                    concurrencyLimit=concurrencyLimit, hog=hog))
        return name

    def step(self, name, depends=[], commands=[], hog=False, memory=None,
             arrayParamValues=None, workflowTasksPerGridTask=1, priority=0,
             resources={}, concurrencyLimit = None):
        self._checkname(name)
        depends = wraplist(depends, 'depends')
        for dep in depends:
            if _findstep(dep, self.steps) is None:
                raise RuntimeError('step named %s does not exist' % dep)
        commands = wraplist(commands, 'commands')
        for c in commands:
            if c.strip()[-1] == '&':
                raise RuntimeError('commands must not end with "&"')

        if arrayParamValues is None:
            arrayParamValues = []
        elif 0 == len(arrayParamValues):
            raise RuntimeError('arrayParamValues has 0 elements')

        # Validate and set resource defaults.
        resources = resources.copy() # shallow copy
        if (memory is not None) and resources.has_key('memorymb'):
            raise RuntimeError('both memory and memorymb resource cannot be specified in a single step')
        if memory is not None:
            resources['memorymb'] = int(memory*1024)
        if 'cpu' not in resources:
            resources['cpu'] = 100
        if 'memorymb' not in resources:
            resources['memorymb'] = 1024
        memory = float(resources['memorymb'] / 1024)
        self.steps.append(bundle(name=name, depends=depends, commands=commands,
                                 hog=hog, memory=memory, resources=resources, priority=priority,
                                 arrayParamValues=arrayParamValues,
                                 workflowTasksPerGridTask=workflowTasksPerGridTask,
                                 concurrencyLimit=concurrencyLimit))
        return name

    def _checkname(self, name):
        if _findstep(name, self.steps) is not None:
            raise RuntimeError('step named %s already exists' % name)
        if _findstep(name, self.services) is not None:
            raise RuntimeError('step named %s already exists' % name)
