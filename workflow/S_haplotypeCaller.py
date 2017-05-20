# encoding: utf-8
import os

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class haplotypeCaller(Workflow):
    """ haplotypeCaller """

    INIT = bundle(haplotypeCaller=bundle())
    INIT.haplotypeCaller.program = "GenomeAnalysisTK.jar"
    INIT.haplotypeCaller.parameter = "-rf BadCigar"

    def run(self, impl, dependList):
        impl.log.info("step: haplotypeCaller!")
        inputInfo = self.results[dependList[0]].output
        result = bundle(output=bundle(), script=bundle())

        # extend program path
        self.haplotypeCaller.program = self.expath('haplotypeCaller.program')

        if self.file.get("regionVariation"):
            self.haplotypeCaller.parameter += " -L %s " % self.file.regionVariation
        elif self.file.get("region"):
            self.haplotypeCaller.parameter += " -L %s " % self.file.region

        # global param
        ParamDict = self.file.copy()
        ParamDict.update({
            "PROGRAM": "/home/huangzhibo/java -jar {} -T HaplotypeCaller ".format(self.haplotypeCaller.program),
            "REF": self.ref.normal.ref
        })

        # script template
        cmd = ["${PROGRAM} -I ${INPUT} -o ${OUTDIR} -R ${REF} %s" % self.haplotypeCaller.parameter]

        JobParamList = []
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.option.workdir,"scripts",'standalone',sampleName)
            outputPath = impl.mkdir(self.option.workdir, "variation", 'haplotypeCaller', sampleName)
            result.output[sampleName] = os.path.join(outputPath, "{}.hc.vcf.gz".format(sampleName))

            # global param
            JobParamList.append({
                "SAMPLE": sampleName,
                "SCRDIR": scriptsdir,
                "INPUT": inputInfo[sampleName],
                "OUTDIR": result.output[sampleName]
            })

        # write script
        scriptPath = \
            impl.write_scripts(
                name='haplotypeCaller',
                commands=cmd,
                JobParamList=JobParamList,
                paramDict=ParamDict)

        # result
        result.script.update(scriptPath)
        return result
