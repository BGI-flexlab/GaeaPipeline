# encoding: utf-8

from gaeautils.bundle import bundle
from gaeautils.workflow import Workflow


class HelloWorld(Workflow):
    " An example for APP develop. (samtools index). "

    #INIT 设置默认参数。 
    INIT = bundle(HelloWorld=bundle())
    INIT.HelloWorld.program = "/home/huangzhibo/bin/samtools"  #若user.conf中设置了HelloWorld.program, 则此值会被覆盖
    INIT.HelloWorld.parameter = ''
    INIT.HelloWorld.mem = '2G'    #standalone 需要设置所需计算资源 (用于向集群提交任务)
    

    def run(self, impl, dependList):
        '''
        dependList是该步骤的依赖步骤列表，如［'S','HelloWorld','bamSort']，则dependList==['bamSort']
        self.results是一个包装了的字典类型（bundle，可通过'.'取值），其中存储了各步骤的输出信息, 如下
        self.results = \
        {
            "bamSort": {
                "output": {
                    "sample1": "/path/sample1.bam", 
                    "sample2": "/path/sample2.bam"
                }, 
                "script": {
                    "sample1": "/path/sample1/bamSort.sh", 
                    "sample2": "/path/sample2/bamSort.sh"
                }
            },
            ...
        }
        从self.results中获取bamSort步骤的输出信息：inputInfo = self.results.bamSort.output
        '''
        
        impl.log.info("step: HelloWorld!")
        inputInfo = self.results[dependList[0]].output
        
        #result 定义返回值，将被赋值给 self.results.HelloWorld, 其中script必须设置用以提交任务，output如果不设置则该APP不能被依赖
        result = bundle(output=bundle(),script=bundle()) 
        
        #extend program path (get abs path)
        self.HelloWorld.program = self.expath('HelloWorld.program')
        
        #script template  生成脚本，cmd是个列表，每个值生成shell脚本的一行,${XXX}将被ParamDict中的值替换
        cmd = []
        cmd.append('%s index ${PARAM} ${INPUT}' % self.HelloWorld.program)
        cmd.append('echo "Hello World!"')
            
        for sampleName in inputInfo:
            scriptsdir = impl.mkdir(self.scriptsDir,'standalone',sampleName)
            
            ParamDict = {
                    "INPUT": inputInfo[sampleName],
                    "PARAM":self.HelloWorld.parameter
                }
            
            #write script
            scriptPath = \
            impl.write_shell(
                    name = 'HelloWorld',
                    scriptsdir = scriptsdir,
                    commands=cmd,
                    paramDict=ParamDict)
            
            #result
            result.output[sampleName] = inputInfo[sampleName]
            result.script[sampleName] = scriptPath
        return result
                                
