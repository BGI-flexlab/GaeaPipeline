from gaeautils import bundle, Logger
import glob
import os


logger = Logger('log.txt','2',"mode5",True).getlog()
def parse_sample(sampleList):
    
    total_number = 0
    with open(sampleList,'r') as f:
        sampleInfo = bundle()
        for line in f:
            total_number += 1
            line = line.strip()
            field = line.split()
            sampleName = field[0]
            fq1 = field[1]
            fq2 = ''
            if len(field) >= 3:
                fq2 = field[2]
            if os.path.exists(fq1):
                logger.error("%s under %s don't exists." % (fq1,sampleName))
                exit(3)
            fq_dir = os.path.dirname(fq1)
            fq_name = os.path.basename(fq1)
        
            #date_md_flowcell_laneID_lib
            #100920_I126_FC801V9ABXX_L6_HUMlatXAOIDCBAPEI-8_2.fq
            tmp = fq_name.split("_")
            rg_ID = tmp[4]+"_"+tmp[2]+"-"+tmp[3]
            rg_PU = tmp[0]+"_"+tmp[1]+"_"+tmp[2]+"_"+tmp[3]+"_"+tmp[4]
            rg_LB = tmp[4]
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
                logger.warning("%s of line: %d is SE data!" % (sampleName,total_number))
                
            sampleInfo[sampleName][dataTag]['rg'] = rg
            sampleInfo[sampleName][dataTag]['libname'] = fq_lib_name
            
    return sampleInfo