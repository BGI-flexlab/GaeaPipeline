#!/usr/bin/python

import sys, os, re
import json
# try:
#     import json
# except:
#     import simplejson as json
import bundle

def dumps(obj):
    return json.dumps(obj, indent=2)

def dump(obj, filename):
    f = open(filename, 'w')
    try:
        json.dump(obj, f, indent=2)
        print >>f, ''
    finally:
        f.close()

# Motivation for this horror: when simplejson works in pure-python mode,
# it behaves differently from the C-speedups mode. All strings are returned
# as unicode, and object hooks don't work. This function replaces unicode
# with str and dicts with bundles.

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

def loads(s):
    return clean( json.loads(s) )

def load(filename):
    f = open(filename, 'r')
    try:
        return clean( json.load(f) )
    finally:
        f.close()

def flatten(obj, objName='<top>'):
    """Returns a flattened representation of a recursively aggregate obj.
    Flattenning means that aggregate data structures (dict, list, bundle)
    on all levels of hierarchy in obj are translated into a series of
    assignments to all the individual elements of the structure, with a
    preceding initialization statement to make these assignments valid.
    Assignments are returned a list of tuple(variable, value).
    When printed with '=' as separator, they yield an executable Python
    code (class cgiutils.bundle has to be imported to make it complete).
    The top of the hierarchy is assigned the name '_' by default.

    For example;

        obj = {
            "A": {
                "profile": false,
                "map": {
                    "mateGapRange": [
                        0,
                        700
                    ],
                    "samplingFraction": 1
                },
                "idqcRootDir": "/prod/pv-01/pipeline/IDQC"
            }
        }
        for k, v in flatten(obj, 'init'):
            print k, "=", v

    will print:

        init = {}
        init.A = {}
        init.A.profile = False
        init.A.map = {}
        init.A.map.mateGapRange = [None] * 2
        init.A.map.mateGapRange.[0] = 0
        init.A.map.mateGapRange.[1] = 700
        init.A.map.samplingFraction = 1
        init.A.idqcRootDir = "/prod/pv-01/pipeline/IDQC"
    """

    r = []
    if isinstance(obj, ( dict, bundle )):
        if objName:
            r += [ ( objName, 'bundle()' ) ]
        for k, v in obj.iteritems():
            if re.match(r'^[A-Za-z]\w*$', k):
                r += flatten(v, '%s%s%s' % ( objName, objName and '.' or '', k ))
            else:
                r += flatten(v, '%s["%s"]' % ( objName, k ))
    elif isinstance(obj, list):
        if len(obj) == 0:
            r += [ ( objName, '[]' ) ]
        else:
            r += [ ( objName, '[None] * %d' % len(obj) ) ]
        for i, v in enumerate(obj):
            r += flatten(v, '%s[%d]' % ( objName, i ))
    else:
        if isinstance(obj, str):
            r += [ ( objName, '"' + obj + '"' ) ]
        else:
            r += [ ( objName, obj ) ]
    return r

def dumpsFlat(obj, objName='top'):
    """Returns a flattened representation of obj as a string. See flatten() above."""
    r = []
    for (k, v) in flatten(obj, objName):
        r += [ "%s = %s" % (k, v) ]
    return "\n".join(sorted(r))

def dumpFlat(obj, filename, objName='top'):
    """Dumps a flattened representation of obj to a file. See flatten() above."""
    f = open(filename, 'w')
    try:
        print >>f, "#!/usr/bin/env python",
        print >>f
        print >>f, "from cgiutils import bundle"
        print >>f, "from wfclib import jsonutil"
        print >>f
        print >>f, dumpsFlat(obj, objName)
        print >>f
        print >>f, "# Example of what can be done with %s:" % objName
        print >>f, "print jsonutil.dumps(%s)" % objName
    finally:
        f.close()

class DictDiff:
    def __init__(self, dictOld, dictNew):
        self.deleted = []
        self.added = []
        self.changed = []
        self.unchanged = []

        for key in sorted(set(dictOld.keys() + dictNew.keys())):
            inOld = key in dictOld
            inNew = key in dictNew

            if inOld and not inNew:
                self.deleted.append(( key, dictOld[key] ))
            elif not inOld and inNew:
                self.added.append(( key, dictNew[key] ))
            elif dictOld[key] != dictNew[key]:
                self.changed.append(( key, dictOld[key], dictNew[key] ))
            else:
                self.unchanged.append(( key, dictOld[key] ))

    def __dumps(self, format, cont):
        return '\n'.join(map(lambda x: format % x, cont))

    def dumpsAdded(self, format):
        return self.__dumps(format, self.added)

    def dumpsDeleted(self, format):
        return self.__dumps(format, self.deleted)

    def dumpsChanged(self, format):
        return self.__dumps(format, self.changed)

    def dumpsUnchanged(self, format):
        return self.__dumps(format, self.unchanged)

def flatDiff(objOld, objNew, objName='<top>'):
    flatObjOld = dict(flatten(objOld, objName))
    flatObjNew = dict(flatten(objNew, objName))
    return DictDiff(flatObjOld, flatObjNew)
