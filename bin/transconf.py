#!/usr/bin/env python

import collections
from gaeautils import clean
from optparse import OptionParser
import subprocess
import sys, json
import time

from configobj import ConfigObj


def printtime(message, *args):
    if args:
        message = message % args
    print "[ " + time.strftime('%X') + " ] " + message
    sys.stdout.flush()
    sys.stderr.flush()

def RunCommand(command,description):
    printtime(' ')
    printtime('Task    : ' + description)
    printtime('Command : ' + command)
    printtime(' ')
    stat = subprocess.call(command,shell=True)
    if stat != 0:
        printtime('ERROR: command failed with status %d' % stat)
        sys.exit(1)

def write_ini(confdict,filename):
    cfg = ConfigObj(confdict)
    cfg.filename = filename
    cfg.write()

def analysis_option_trans(stepList):
    dependList = []
    for n,step in enumerate(stepList):
        if step == 'filter':
            dependList.append(['H','filter'])
        elif step == 'alignment':
            if 'filter' in stepList[:n+1]:
                dependList.append(['H','alignment','filter'])
            else:
                dependList.append(['H','alignment'])
        elif step == 'removeduplicates':
            if 'alignment' in stepList[:n+1]:
                dependList.append(['H','rmdup','alignment'])
            else:
                dependList.append(['H','rmdup'])
        elif step == 'realignment':
            if 'removeduplicates' in stepList[:n+1]:
                dependList.append(['H','realignment','rmdup'])
            elif 'alianment' in stepList[:n+1]:
                dependList.append(['H','realignment','alignment'])
            else:
                dependList.append(['H','realignment'])
        elif step == 'baserecal':
            if 'realignment' in stepList[:n+1]:
                dependList.append(['H','baserecal','realignment'])
            elif 'removeduplicates' in stepList[:n+1]:
                dependList.append(['H','baserecal','rmdup'])
            elif 'alianment' in stepList[:n+1]:
                dependList.append(['H','baserecal','alignment'])
            else:
                dependList.append(['H','baserecal'])
        elif step == 'bamqc':
            if 'baserecal' in stepList[:n+1]:
                dependList.append(['H','bamqc','baserecal'])
            elif 'realignment' in stepList[:n+1]:
                dependList.append(['H','bamqc','realignment'])
            elif 'removeduplicates' in stepList[:n+1]:
                dependList.append(['H','bamqc','rmdup'])
            elif 'alianment' in stepList[:n+1]:
                dependList.append(['H','bamqc','alignment'])
            else:
                dependList.append(['H','bamqc'])
        elif step == 'genotype':
            if 'baserecal' in stepList[:n+1]:
                dependList.append(['H','genotype','baserecal'])
            elif 'realignment' in stepList[:n+1]:
                dependList.append(['H','genotype','realignment'])
            elif 'removeduplicates' in stepList[:n+1]:
                dependList.append(['H','genotype','rmdup'])
            elif 'alianment' in stepList[:n+1]:
                dependList.append(['H','genotype','alignment'])
            else:
                dependList.append(['H','genotype'])
            dependList.append(['H','mergeVariant','genotype'])
        elif step == 'bamSort':
            if 'baserecal' in stepList[:n+1]:
                dependList.append(['H','bamSort','baserecal'])
            elif 'realignment' in stepList[:n+1]:
                dependList.append(['H','bamSort','realignment'])
            elif 'removeduplicates' in stepList[:n+1]:
                dependList.append(['H','bamSort','rmdup'])
            elif 'alianment' in stepList[:n+1]:
                dependList.append(['H','bamSort','alignment'])
            else:
                dependList.append(['H','bamSort'])
        elif step == 'cgConversion':
            if 'genotype' in stepList[:n+1]:
                dependList.append(['S','cgConversion','bamSort,mergeVariant'])
        elif step == 'cnv':
            if 'genotype' in stepList[:n+1]:
                dependList.append(['S','cnv','bamqc'])
        elif step == 'newCnv':
            if 'genotype' in stepList[:n+1]:
                dependList.append(['S','newCnv','bamqc'])
        elif step == 'graph':
            if 'genotype' in stepList[:n+1]:
                dependList.append(['S','graph','bamqc'])
        elif step == 'BGICGAnnotation':
            if 'genotype' in stepList[:n+1]:
                dependList.append(['S','BGICGAnnotation','mergeVariant'])
            else:
                dependList.append(['S','BGICGAnnotation'])
        else:
            printtime('WARNING: unknown step ( %s ) be trans to ["S",%s,%s] ' % (step,stepList[n-1]))
            if n == 0:
                printtime('WARNING: unknown step ( %s ) be trans to ["S",%s] ' % step)
                dependList.append(['S',step])
            elif 'genotype' in stepList[:n+1]:
                printtime('WARNING: unknown step ( %s ) be trans to ["S",%s,%s] ' % (step,stepList[n-1]))
                dependList.append(['S',step,stepList[n-1]])
            elif not 'genotype' in stepList[:n+1]:
                printtime('WARNING: unknown step ( %s ) be trans to ["H",%s,%s] ' % (step,stepList[n-1]))
                dependList.append(['H',step,stepList[n-1]])
    return dependList

def main():
    
    parser = OptionParser()
    parser.add_option('-i', '--oldconf',       help='Input old Gaea conf file', dest='oldconf',metavar='FILE')
    parser.add_option('-o', '--newconf',       help='Output new Gaea conf file', dest='newconf',metavar='FILE')    
    parser.add_option('-m', '--maplist',       help='The map-list of oldkeys and newkeys,default:("/ifs4/ISDC_BD/huangzhibo/GaeaPipeline/tools/transConf.list")', dest='maplist',metavar='FILE')    
    parser.add_option('-t', '--filetype',     choices=['1','2','3'], help='output file type(1: oldconf->json, 2: oldconf->ini, 3: json->ini),[deflaut: 1]', dest='filetype',metavar='int')    
    (options, args) = parser.parse_args()
	
    if not options.oldconf or not options.newconf:
        parser.print_help()
        exit(1)

    confdict = collections.OrderedDict()
    filetype = int(options.filetype)
    if filetype == 3:
        with open(options.oldconf,'r') as f:
            confdict = json.load(f,object_pairs_hook=collections.OrderedDict)
            write_ini(clean(confdict),options.newconf)
            return 0

    if not options.maplist:
        options.maplist = "/ifs4/ISDC_BD/huangzhibo/GaeaPipeline/tools/transConf.list"

    mapfile = open(options.maplist,'r')
    mapdict = dict()
    for line in mapfile:
        line = line.strip()
        keylist = line.split(':')
        if len(keylist) == 1:
            mapdict[keylist[0]] = keylist[0].replace('_','.')
        elif len(keylist) == 2:
            mapdict[keylist[0]] = keylist[1]
        else:
            printtime('ERROR: bad maplist format')

    mustProperty = ['analysis_flow','file','hadoop','ref','init']
    for mp in mustProperty:
        confdict[mp] = collections.OrderedDict()

    infile = open(options.oldconf,'r')
    for line in infile:
        line = line.strip()
        if not line or line[0]=='#':
            continue
        fields = line.split('=')
        k = fields[0].strip()
        fields[1] = fields[1].strip()        
                

        if not mapdict.has_key(k):
            continue
        li = mapdict[k].split('.')
        if len(li) == 1:
            if k == 'analysis_option':
                stepList = analysis_option_trans(fields[1].split(','))
                for (n,sl) in enumerate(stepList):
                    key = "key" + str(n)
                    confdict[li[0]][key] = sl
            else:
                confdict[li[0]] = fields[1]
        elif len(li) == 2:
            if not confdict.has_key(li[0]):
                confdict[li[0]] = collections.OrderedDict()
            confdict[li[0]][li[1]] = fields[1]
        elif len(li) == 3:
            if not confdict.has_key(li[0]):
                confdict[li[0]] = collections.OrderedDict()
            if not confdict[li[0]].has_key(li[1]):
                confdict[li[0]][li[1]] = {}
            confdict[li[0]][li[1]][li[2]] = fields[1]
    if filetype == 2:
        write_ini(confdict, options.newconf)
    else:
        json.dump(confdict, open(options.newconf, 'w'),indent=4)

if __name__ == '__main__':
    main()
