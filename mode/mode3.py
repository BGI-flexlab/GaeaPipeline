from gaeautils import bundle

def parse_sample(sampleList):
    
    with open(sampleList,'r') as f:
        sampleInfo = bundle()
        for line in f:
            line = line.strip()
            tmp = line.split()
            sampleInfo[tmp[0]] = tmp[1]
    return sampleInfo