# encoding: utf-8
from gaeautils import bundle
import os


class Workflow(object):
    '''
    The basic class of each APP
    '''
    INIT = bundle()
    fs_cmd = bundle()
    
    result = bundle(output=bundle(),script=bundle())
    ParamDict = bundle()
    JobParamList = []
    cmd = []
    
    def __init__(self,state):
        self.__dict__.clear()
        self.__dict__.update(state) 
        hadoop = self.hadoop.bin
        if self.hadoop.has_key('fs_mode') and self.hadoop.fs_mode == 'hdfs':
            
            if self.hadoop.has_key('ishadoop2'):
                if isinstance(self.hadoop.ishadoop2, str):
                    if self.hadoop.ishadoop2.upper() == 'FALSE':
                        self.hadoop.ishadoop2 = False
                    else:
                        self.hadoop.ishadoop2 = True
                
            if self.hadoop.ishadoop2:
                self.fs_cmd.delete = "%s fs -rm -r -skipTrash " % hadoop
                self.fs_cmd.mkdir = "%s fs -mkdir " % hadoop
                self.fs_cmd.put = "%s fs -put " % hadoop
                self.fs_cmd.cp = "%s fs -copyToLocal " % hadoop
                self.fs_cmd.ls = "%s fs -ls " % hadoop
            else:
                self.fs_cmd.delete = "%s dfs -rmr -skipTrash " % hadoop
                self.fs_cmd.mkdir = "%s dfs -mkdir " % hadoop
                self.fs_cmd.put = "%s dfs -put " % hadoop
                self.fs_cmd.cp = "%s dfs -copyToLocal " % hadoop
                self.fs_cmd.ls = "%s dfs -ls " % hadoop
        elif self.hadoop.has_key('is_at_TH') and self.hadoop.is_at_TH:
            self.fs_cmd.delete = "rm -rf "
            self.fs_cmd.mkdir = "mkdir -p "
            self.fs_cmd.put = "ln -s "
            self.fs_cmd.cp = "cp -r "
            self.fs_cmd.ls = "ls -l "
        else:
            self.fs_cmd.delete = "rm -rf "
            self.fs_cmd.mkdir = "mkdir -p "
            self.fs_cmd.put = "ln -s "
            self.fs_cmd.cp = "cp -rf "
            self.fs_cmd.ls = "ls -l "
        state.fs_cmd = self.fs_cmd
        
    def expath(self, paramName, mustBe = True):
        field = paramName.split('.')
        state = self.__dict__
        if len(field) == 1:
            path_tmp = state[field[0]]
        elif len(field) == 2:
            path_tmp = state[field[0]][field[1]]
        elif len(field) == 3:
            path_tmp = state[field[0]][field[1]][field[2]]
        elif len(field) == 4:
            path_tmp = state[field[0]][field[1]][field[2]][field[3]]
        elif len(field) == 5:
            path_tmp = state[field[0]][field[1]][field[2]][field[3]][field[4]]
        else:
            raise RuntimeError('paramName (%s) is wrong!' % paramName)


        if not path_tmp:
            if mustBe:
                raise RuntimeError('Program is not exists: %s' % paramName)
            else:
                return ''

        if os.path.exists(path_tmp):
            return path_tmp
        else:
            for p in self.Path.prgDir.split(':'):
                if os.path.exists(os.path.join(p, path_tmp)):
                    return os.path.join(p, path_tmp)

        if mustBe:
            raise RuntimeError('Program is not exists: %s = %s' % (paramName,path_tmp))
        else:
            return path_tmp

    def main(self,impl, dependList):
        self.run(impl, dependList)
        
        print self.__class__.__name__
        #write script
         
        scriptPath = \
        impl.write_scripts(
                name = self.__class__.__name__,
                commands=self.cmd,
                JobParamList=self.JobParamList,
                paramDict=self.ParamDict)
     
        #result
        self.result.script.update(scriptPath)        
        return self.result
#