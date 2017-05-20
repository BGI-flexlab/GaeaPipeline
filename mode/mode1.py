import glob
import os

from gaeautils import Logger
from gaeautils import bundle

logger = Logger('log.txt','2',"mode1",True).getlog()
def parse_sample(sampleList):
    sample_lane_counter = 0
    total_number = 0
    insert_size = ''
    fq1s = []
    
    with open(sampleList,'r') as sampleFile:
        sampleInfo = bundle()
        for line in sampleFile:
            line = line.strip()
            #sample_name, gender, family, type, pool, fq1, fq2, insert_size, fq1s
            field = line.split()
            field_num = len(field)
            sampleName = field[0]
            if field_num >= 6:
                gender = field[1]
                family = field[2]
                thetype = field[3]
                pool = field[4]
                fq1 = field[5]
                fq2 = ''
                if not os.path.isfile(fq1):
                    if os.path.isdir(fq1) and field_num >= 8:
                        pub_path = fq1
                        pooling = field[6]
                        lib = field[7]
                        fq1s = glob.glob("%s/*/%s/*%s/*%s*_1.fq.gz" % (pub_path,pooling,lib,lib))
                        if len(fq1s) == 0:
                            raise RuntimeError("fq1 don't exists at pooling:%s & lib:%s" % (pooling,lib))
                    else:
                        raise RuntimeError("%s don't exists!" % fq1)
                else:
                    fq1s = [fq1]
                    if field_num > 6:
                        fq2 = field[6]
                        if not os.path.isfile(fq2):
                            raise RuntimeError("%s don't exists!" % fq2)
                    if field_num > 7:
                        if int(field[7]) <= 10:
                            raise RuntimeError("wrong insert info:insert size is below 10!")
                        else:
                            insert_size = field[7]
            elif field_num <= 3:
                fq1 = field[1]
                fq2 = field[2]
                fq1s = [fq1]

            for fq1 in fq1s:
                total_number += 1
                fq_dir = os.path.abspath(os.path.dirname(fq1))
                fq_name = os.path.basename(fq1)
                
                #date_md_flowcell_laneID_lib
                #100920_I126_FC801V9ABXX_L6_HUMlatXAOIDCBAPEI-8_2.fq
                tmp = fq_name.split("_")
                rg_ID = tmp[4]+"_"+tmp[2]+"-"+tmp[3]
                rg_PU = tmp[0]+"_"+tmp[1]+"_"+tmp[2]+"_"+tmp[3]+"_"+tmp[4]
                rg_LB = sampleName + "_" + tmp[4]
                rg = "@RG\\tID:%s\\tPL:illumina\\tPU:%s\\tLB:%s\\tSM:%s\\tCN:BGI" % (rg_ID,rg_PU,rg_LB,sampleName)
                fq_lib_name = rg_ID
                 
                if not sampleInfo.has_key(sampleName):
                    sampleInfo[sampleName] = bundle()
                    sample_lane_counter = 0
                else:
                    sample_lane_counter = len(sampleInfo[sampleName])
                    
                dataTag = 'data'+str(sample_lane_counter)
                if not sampleInfo[sampleName].has_key(dataTag):
                    sampleInfo[sampleName][dataTag] = bundle()
                
                #find adp1
                sampleInfo[sampleName][dataTag]['fq1'] = fq1
                adp1 = glob.glob("%s/*1.adapter.list*" % fq_dir)
                if adp1:
                    adp1_file = adp1[0].strip()
                    sampleInfo[sampleName][dataTag]['adp1'] = adp1_file
                else:
                    sampleInfo[sampleName][dataTag]['adp1'] = 'null'
                    
                #find fq2 and adp2
                fq2 = fq1
                fq2 = fq2.replace("1.fq.gz", "2.fq.gz")
                if os.path.exists(fq2):
                    sampleInfo[sampleName][dataTag]['fq2'] = fq2
                    adp2 = glob.glob("%s/*2.adapter.list*" % fq_dir)
                    if adp2:
                        adp2_file = adp2[0].strip()
                        sampleInfo[sampleName][dataTag]['adp2'] = adp2_file
                    else:
                        sampleInfo[sampleName][dataTag]['adp2'] = 'null'
                else:
                    logger.info("%s of line: %d is SE data!" % (sampleName,total_number)) 
                    
                sampleInfo[sampleName][dataTag]['gender'] = gender
                sampleInfo[sampleName][dataTag]['family'] = family
                sampleInfo[sampleName][dataTag]['type'] = thetype
                sampleInfo[sampleName][dataTag]['pool'] = pool
                sampleInfo[sampleName][dataTag]['rg'] = rg
                sampleInfo[sampleName][dataTag]['libname'] = fq_lib_name
                
                if insert_size:
                    sampleInfo[sampleName][dataTag]['insert_size'] = insert_size
                    
    return sampleInfo
                                        
