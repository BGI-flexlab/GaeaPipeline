#!/usr/bin/env python
import sys
import os
import gzip
from optparse import OptionParser

def getQualitySystem(fqfile, line_num=100):
    
    if os.path.splitext(fqfile)[1] == '.gz':	
        inputFile = gzip.open(fqfile,'rt')		
    else:
        inputFile = open(fqfile,'r')

    qs_set = set()
    n = 0
    for line in inputFile:
        if n > line_num:
            break
        n += 1
        inputFile.readline()
        inputFile.readline()
        qs = inputFile.readline()
        qs_set.update(qs[:-1])
    min = 'h'
    max = '!'
    for c in qs_set:
        min = min > c and c or min
        max = max < c and c or max
    if max > 'J' and min > ':':
        return 1
    elif max <= 'K' and min <= ':':
        return 0
    elif max <= 'K' and min > ':':
        return -1
    else:
        print "Cann't check quilitySystem, please set it in user.cfg: init.qualitySystem!"
        exit(1)
