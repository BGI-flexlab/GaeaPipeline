#!/usr/bin/python
from copy import deepcopy

class bundle(dict):
    '''Dictionary where keys must be strings and values can be
       accessed by x.keyName as well as the usual x['keyName'] as
       long as the key is a valid identifier'''
    __slots__ = ()

    # __getattr__ = dict.__getitem__
    def __getattr__(self, key):
        if key.startswith('__'):
            return dict.__getattr__(key)
        else:
            return dict.__getitem__(self, key)
    __delattr__ = dict.__delitem__
    __setattr__ = dict.__setitem__

    def __setitem__(self, key, val):
        if isinstance(key, str):
            dict.__setitem__(self, key, val)
        else:
            raise TypeError('bundle keys must be strings')

    def rupdate(self, other, checkCompat=False, keyPath=None):
        '''Recursive update: similar to dict.update(), but merges bundle-typed
           values instead of overwriting the old one'''

        for k, v in other.iteritems():
            if k in self:
                if keyPath is None:
                    newKeyPath = k
                else:
                    newKeyPath = '.'.join( [ keyPath, k ] )

                if isinstance(self[k], bundle) and isinstance(v, dict):
                    self[k].rupdate(v, checkCompat=checkCompat, keyPath=newKeyPath)
                elif v != self[k]:
                    if  checkCompat:
                        raise Exception(
                            'combining bundles: incompatible key definition for %s: was: %s, now: %s' %
                                (newKeyPath, str(self[k]), v))
                    else:
                        self[k] = deepcopy(v)
            else:
                self[k] = deepcopy(v)

    def rcopy(self):
        '''Recursive copy'''
        r = bundle()
        for k, v in self.iteritems():
            if isinstance(v, bundle):
                r[k] = v.rcopy()
            else:
                r[k] = deepcopy(v)
        return r
