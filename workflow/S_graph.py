# encoding: utf-8
import commands
from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow
import os

class graph(Workflow):
    """ standalone step : graph """

    INIT = bundle(graph=bundle())
    INIT.graph.uncoverAnno = ''
    INIT.graph.gaeaInsertsize = ''
    INIT.graph.exonGraph = ''
    INIT.graph.totalCoverageDepth = ''
    INIT.graph.depthAccumlate = ''
    INIT.graph.mem = '3G'

    def run(self, impl,dependList):
        impl.log.info("step: graph!")
        result = bundle(script=bundle())
        
        self.graph.uncoverAnno = self.expath('graph.uncoverAnno',False)
        self.graph.exonGraph = self.expath('graph.exonGraph',False)
        self.graph.totalCoverageDepth = self.expath('graph.totalCoverageDepth',False)
        self.graph.depthAccumlate = self.expath('graph.depthAccumlate',False)
        
        _,output =  commands.getstatusoutput('perl %s/bin/require_config.pl %s' % (self.GAEA_HOME,self.file.annoProtoclConfig))
        config = eval(output)
        
        scriptsdir = impl.mkdir(self.option.workdir,"scripts",'standalone',self.option.multiSampleName)
        
        ParamDict = {
                "WORKDIR" : self.option.workdir,
                "uncoverAnno" : self.graph.get('uncoverAnno'),
                "exonGraph" : self.graph.get('exonGraph'),
                "totalCoverageDepth" : self.graph.get('totalCoverageDepth'),
                "depthAccumlate" : self.graph.get('depthAccumlate')
            }
        
        #script template    
        cmd = []
        if os.path.exists('/ifs4/'):
            cmd.append("export PATH=/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/HPC_chip/tools:$PATH")
            cmd.append("export HPC_CHIP_HOME=/ifs5/ST_TRANS_CARDIO/PUB/analysis_pipelines/HPC_chip")
            
        if self.graph.get('exonGraph'):
            graph_trans = ''
            if config.get("graph_trans"):
                graph_trans = '-graph_trans %s' % config["graph_trans"]
            else:
                impl.log.warning("No config.graph_trans value!")
                
            cmd.append('echo "exon graph:"')
            cmd.append("for i in `ls ${WORKDIR}/QC/*/*anno_region.txt`;do")
            cmd.append("perl ${exonGraph} -output ${WORKDIR}/QC/graph/exon_graph -exon_data $i %s;\ndone\n" % graph_trans )
        
        if self.graph.get('gaeaInsertsize'):
            outdir = impl.mkdir("%s/QC/graph/Insertion" % self.option.workdir)
            cmd.append('echo "gaea-insertsize:"')
            cmd.append('for i in `ls ${WORKDIR}/QC/*/*insert.xls`;do')
            cmd.append("sampleName=`ls $i|awk -F '/' '{print $NF}' |awk -F '.' '{print $1}'`")
            cmd.append('Rscript %s $i $sampleName ${WORKDIR}/QC/graph/Insertion/$sampleName\\_insert.png;\ndone\n' % self.graph.gaeaInsertsize)
            
        if self.graph.get('totalCoverageDepth'):
            outdir = impl.mkdir("%s/QC/graph/all_sample_depth_pic" % self.option.workdir)
            with open(os.path.join(self.option.workdir,'temp/bam_qc.list'),'w') as f:
                for sample in self.sample:
                    bamqc_file = ''
                    if self.option.multi:
                        bamqc_file = os.path.join(self.option.workdir, 'QC', self.option.multiSampleName,'%s.bam.report.txt' % sample) 
                    else:
                        bamqc_file = os.path.join(self.option.workdir, 'QC', sample,'%s.bam.report.txt' % sample) 
                    f.write(bamqc_file+'\n')
            cmd.append('echo "total coverage depth:"')
            cmd.append('perl ${totalCoverageDepth}  ${WORKDIR}/temp/bam_qc.list ${WORKDIR}/QC/graph/all_sample_depth_pic -pre gaea-\n')
        if self.graph.get('uncoverAnno'):
            trans = ''
            if config.get("trans"):
                graph_trans = '-trans %s' % config["trans"]
            else:
                impl.log.warning("No config.trans value!")
            cmd.append('echo "uncover_anno:"')
            cmd.append('for i in `ls ${WORKDIR}/QC/*/*unmapped.bed`;do')
            cmd.append('perl ${uncoverAnno} -uncover $i %s -outdir ${WORKDIR}/QC/graph/uncover_anno;\ndone\n' % trans)
            
        if self.graph.get('depthAccumlate'):
            cmd.append('echo "depthAccumlate:"')
            outdir = impl.mkdir("%s/QC/graph/depth_accumlate" % self.option.workdir)
            with open(os.path.join(self.option.workdir,'temp/bam_qc_depth.list'),'w') as f:
                for sample in self.sample:
                    bamqc_file = ''
                    if self.option.multi:
                        bamqc_file = os.path.join(self.option.workdir, 'QC', self.option.multiSampleName,'%s.depth.txt' % sample) 
                    else:
                        bamqc_file = os.path.join(self.option.workdir, 'QC', sample,'%s.depth.txt' % sample) 
                    f.write(bamqc_file+'\n')
            cmd.append('echo "depth accumlate:"')
            cmd.append('perl ${depthAccumlate}  ${WORKDIR}/temp/bam_qc_depth.list %s\n' % outdir)
            
        #write script
        scriptPath = \
        impl.write_shell(
                name = 'graph',
                scriptsdir = scriptsdir,
                commands=cmd,
                paramDict=ParamDict)
        
        #return
        result.script[self.option.multiSampleName] = scriptPath
        return result
                                
