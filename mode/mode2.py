import re

from gaeautils import bundle


def parse_sample(sampleList):
    
    with open(sampleList,'r') as f:
        sampleInfo = bundle()
        sample_lane_counter = 0
        
        for line in f:
            line = line.strip()
            if line[0] == '#':
                continue
            if re.match(r"^\s*$", line):
                continue
            sampleName = ''
            m = re.match(r"^>(\S+)$", line)
            if m:
                sampleName = m.group(1)
                if not sampleInfo.has_key(sampleName):
                    sampleInfo[sampleName] = bundle()
                    sample_lane_counter = 0
                else:
                    sample_lane_counter += 1
                dataTag = 'data' + str(sample_lane_counter)
                sampleInfo[sampleName][dataTag] = bundle()
    
                for info in f:
                    info = info.strip()
                    if info[0] == '#':
                        continue
                    if re.match(r"^\s*$", info):
                        continue
                    m2 = re.match(r"^(\S+)\s*=\s*(\S+)",info)
                    if m2:
                        sampleInfo[sampleName][dataTag][m2.group(1)] = m2.group(2)
                    if re.match(r"^>\s*$", info):
                        break
                
    return sampleInfo