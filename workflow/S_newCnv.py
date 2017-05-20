# encoding: utf-8
from gaeautils import Workflow
from gaeautils import bundle


class newCnv(Workflow):
    """ newCnv """

    INIT = bundle(newCnv=bundle())
    INIT.newCnv.program = "thCNV.pl"
    INIT.newCnv.parameter = ""

    def getPoolingList(self):
        pooling = []
        for sampleName in self.sample:
            pool = self.sample[sampleName].get('pool')
            if pool and pool not in pooling:
                pooling.append(pool)
        return pooling

    def writeSampleList(self,pool_name,scriptdir):
        with open("%s/sample.list" % scriptdir,'w') as fw:
            for sampleName in self.sample:
                pool = self.sample[sampleName].get('pool')
                if pool_name == pool:
                    for dataTag in self.sample[sampleName]['rg']:
                        fw.write("u\t%s-%s\tnull\n"%(sampleName,dataTag))

    def poolingScript(self, impl, scriptsdir):

        cmd = ["cp -r %s %s" % (self.file.cnvRegions, scriptsdir),
               "perl %s %s" % (self.newCnv.program, self.newCnv.parameter)]

        scriptPath = \
            impl.write_shell(
                name='runNewCnv',
                scriptsdir=scriptsdir,
                commands=cmd,
                paramDict=self.file)
        return scriptPath

    def run(self, impl, dependList=None):
        impl.log.info("step: newCnv!")
        # depend bamQC
        result = bundle(script=bundle())

        multi_sample = self.option.multiSampleName
        scriptsdir = impl.mkdir(self.option.workdir, "scripts", 'standalone', multi_sample)


        # extend program path
        self.newCnv.program = self.expath('newCnv.program')
        if self.file.has_key('newCnvConfig'):
            self.file.newCnvConfig = self.expath('file.newCnvConfig')
            self.newCnv.parameter += " %s" % self.file.newCnvConfig
        else:
            raise RuntimeError("newCnv Config file don't exists!")

        if self.file.has_key('cnvRegions'):
            self.file.cnvRegions = self.expath('file.cnvRegions')
        else:
            raise RuntimeError("file.cnvRegions don't exists!")

        poolingList = self.getPoolingList()
        if len(poolingList) == 0:
            raise RuntimeError("pooling info must be setted for CNV analysis!")

        cmd = []
        for pool in poolingList:
            cnvscriptsdir = impl.mkdir(self.option.workdir, "variation", 'cnv', pool)
            script = self.poolingScript(impl, cnvscriptsdir)
            self.writeSampleList(pool,cnvscriptsdir)
            cmd.append("cd %s"% cnvscriptsdir)
            cmd.append("sh %s >%s.o 2>%s.e" % (script, script, script))
            cmd.append('if [ $? -ne 0 ]; then\n\techo "[WARNING]  %s - newCnv failed." >> %s' % (pool, self.logfile))
            cmd.append('\texit 1\nelse')
            cmd.append('\techo "[INFO   ]  %s - newCnv complete." >> %s\nfi\n' % (pool, self.logfile))

        # write script
        scriptPath = \
            impl.write_shell(
                name='newCnv',
                scriptsdir=scriptsdir,
                commands=cmd
            )

        # result
        result.script[multi_sample] = scriptPath
        return result
