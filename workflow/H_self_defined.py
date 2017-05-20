# encoding: utf-8

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow
from string import Template


class self_defined(Workflow):
    " self_defined APP. "

    def run(self, impl, dependList, appname):
        impl.log.info("step: self-defined step %s!" % appname)
        inputInfo = self.results[dependList[0]].output

        result = bundle(output=bundle(), script=bundle())

        # extend program path
        if self.self_defined[appname].has_key('program'):
            self.self_defined[appname].program = impl.expath(self.Path.prgDir, self.self_defined[appname].program)
        else:
            self.self_defined[appname].program = ''

        checkstatus = 'if [ $? -ne 0 ]; then\n\techo "[WARNING]  ${SAMPLE} - %s failed." >> %s\n\texit 1\nelse\n' % (
        appname, self.logfile)
        checkstatus += '\techo "[INFO   ]  ${SAMPLE} - %s complete." >> %s\nfi' % (appname, self.logfile)
        ParamDict = self.file.copy()
        ParamDict.update(self.option)
        ParamDict.update({
            "program": self.self_defined[appname].program,
            "checkstatus": checkstatus
        })

        commandStr = self.self_defined[appname]['command'].strip()
        cmdStr = ''
        for l in commandStr.split('\n'):
            cmdStr += l.strip() + '\n'
        cmdStr = Template(cmdStr.decode('string-escape')).safe_substitute(ParamDict)

        output = self.self_defined[appname].get('output') and self.self_defined[appname]['output'] or ''

        JobParamList = []
        if self.self_defined[appname].get('summary'):
            scriptsdir = impl.mkdir(self.scriptsDir, 'gaea', self.option.multiSampleName)
            JobParamList.append({
                "SAMPLE": self.option.multiSampleName,
                "SCRDIR": scriptsdir
            })
        else:
            for sampleName in inputInfo:
                scriptsdir = impl.mkdir(self.scriptsDir, 'gaea', sampleName)
                if output:
                    outputDict = {
                        "WORKDIR": self.option.workdir,
                        "SAMPLE": sampleName
                    }
                    output = Template(output).safe_substitute(outputDict)
                    result.output[sampleName] = output

                JobParamList.append({
                    "SAMPLE": sampleName,
                    "SCRDIR": scriptsdir,
                    "INPUT": inputInfo[sampleName],
                    "OUTPUT": output
                })

        # write script
        scriptPath = \
            impl.write_scripts(
                name=appname,
                commands=cmdStr,
                JobParamList=JobParamList)

        # result
        result.script.update(scriptPath)
        return result
