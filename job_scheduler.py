#!/usr/bin/env python
import os
import subprocess
import sys
from Queue import Queue
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from threading import Thread, Condition

import time

from gaeautils import printtime
from gaeautils.bundle import bundle
from gaeautils.parseConfig import ParseConfig

__all__ = []
__version__ = '0.1'
__date__ = '2017-05-20'
__updated__ = '2017-05-20'

_sentinel = object()


class Task(Thread):
    def __init__(self, cond, state, queue, ne_queue):
        super(Task, self).__init__()
        self.cond = cond
        self.queue = queue
        self.ne_queue = ne_queue
        self.state = state
        self.ne_step = None
        self.sample_fail = False  # those tasks in this sample is failed

    def _is_exclusive_task(self, task_name):
        for dep_step in self.state.analysisDict[task_name].depend:
            if dep_step in self.ne_step:
                return False

        if 'exclusive_task' not in self.state[task_name]:
            return True

        def astrcmp(x, y):
            return x.lower() == y.lower()

        if astrcmp(self.state[task_name].exclusive_task, 'false') or self.state[task_name].exclusive_task is False:
            return False
        return True

    def _check_log(self, err):
        print err
        status = 'done'
        return status

    def run_task(self, sample, task_name):
        # print self.__class__.__name__, sample, task_name
        script = self.state.results[task_name].script[sample]
        out = open('{}.o'.format(script), 'w')
        err = open('{}.e'.format(script), 'w')
        p = subprocess.Popen('sh {}'.format(script), shell=True, stdout=out, stderr=err)
        p.wait()
        if 'status' not in self.state.results[task_name]:
            self.state.results[task_name].status = {}
        self.state.results[task_name].status[sample] = self._check_log(err)

    def run(self):
        current_sample_name = ''
        while True:
            data = self.queue.get()
            if data is _sentinel:
                self.queue.put(_sentinel)
                break

            (sample, task_name) = data

            if sample == current_sample_name:
                if self._is_exclusive_task(task_name):
                    self.run_task(sample, task_name)
                else:
                    self.ne_step.add(task_name)
                    self.ne_queue.put((sample, task_name))
            else:
                current_sample_name = sample
                self.ne_step = set()
                self.run_task(sample, task_name)
            self.queue.task_done()


class NonExclusiveTask(Task):
    def __init__(self, cond, state, queue, ne_queue):
        super(NonExclusiveTask, self).__init__(cond, state, queue, ne_queue)
        self.ne_step = None  # todo 将独占任务及其依赖任务放回queue

    def _is_exclusive_task(self, task_name):
        if 'exclusive_task' not in self.state[task_name]:
            return False

        def astrcmp(x, y):
            return x.lower() == y.lower()

        if astrcmp(self.state[task_name].exclusive_task, 'false') or self.state[task_name].exclusive_task is False:
            return False
        return True

    def run(self):
        while True:
            data = self.ne_queue.get()
            if data is _sentinel:
                self.ne_queue.put(_sentinel)
                break
            (sample, task_name) = data
            if self._is_exclusive_task(task_name):
                self.queue.put((sample, task_name))
            else:
                self.run_task(sample, task_name)
            self.ne_queue.task_done()


class Scheduler(object):
    def __init__(self, state):
        self.state = state
        self.samples = []
        self.task_lists = []
        self.task_t = None
        self.nx_task_t = None

    def parse_rerun(self, rerun_list_file):
        with open(rerun_list_file, 'r') as f:
            for n, line in enumerate(f):
                (sample, tasks) = line.strip().split('\t')
                task_list = tasks.split(',')
                self.samples.append(sample)
                self.task_lists.append(task_list)

    def start(self):
        task_queue = Queue()
        non_exclusive_task_queue = Queue()
        cond = Condition()
        self.task_t = Task(cond, self.state, task_queue, non_exclusive_task_queue)
        # self.task_t.setDaemon(True)
        self.task_t.start()

        self.nx_task_t = NonExclusiveTask(cond, self.state, task_queue, non_exclusive_task_queue)
        # self.nx_task_t.setDaemon(True)
        self.nx_task_t.start()

        for sample, task_list in zip(self.samples, self.task_lists):
            task_queue.join()
            for task_name in task_list:
                task_queue.put((sample, task_name))

        task_queue.join()
        non_exclusive_task_queue.join()
        task_queue.put(_sentinel)
        non_exclusive_task_queue.put(_sentinel)


def main():
    program_name = os.path.basename(sys.argv[0])
    program_license = '''{0}
      Created by huangzhibo on {1}.
      Last updated on {2}.
      Copyright 2017 BGI bigData. All rights reserved.
    USAGE'''.format(" v".join([program_name, __version__]), str(__date__), str(__updated__))

    parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-s", "--state", dest="state", help="state file,[default: %(default)s]", required=True)
    parser.add_argument("-r", "--rerun", dest="rerun", help="rerun file,[default: %(default)s]", required=True)

    if len(sys.argv) == 1:
        parser.print_help()
        exit(1)

    # Process arguments
    args = parser.parse_args()
    if not os.path.exists(args.state):
        printtime('ERROR: (--state: %s) - No such file or directory' % args.state)
        return 1
    if not os.path.exists(args.rerun):
        printtime('ERROR: (--state: %s) - No such file or directory' % args.state)
        return 1

    state = ParseConfig(args.state).parseState()

    sched = Scheduler(state)
    sched.parse_rerun(args.rerun)
    sched.start()

    return 0


if __name__ == "__main__":
    sys.exit(main())
