"""Main Mannhunter class and utilities"""

from __future__ import print_function

import logging
import time
import os

import psutil
import supervisor.childutils
import supervisor.datatypes


def percentage(x, y):
    return float(x) / float(y) * 100


class Interval(object):
    """Sleeps for the time since the interval was last reset when called"""

    def __init__(self, interval):
        self.interval = interval
        self.reset()

    def __call__(self):
        time.sleep(self.interval - (time.time() - self.last))
        self.reset()
        return True

    def reset(self):
        self.last = time.time()


class Mannhunter(object):
    def __init__(self, host, port):
        self.log = logging.getLogger('mannhunter')
        self.log.info("I'm going to stop you, now.")
        self.supervisor = supervisor.childutils.getRPCInterface(os.environ)

        self.monitoring = {
            'supermann3': {
                'memory': supervisor.datatypes.byte_size('20MB')
            },
            'memory_leak': {
                'memory': supervisor.datatypes.byte_size('100MB')
            }
        }

        self.limits = {
            'memory': self.limit_memory
        }

        for program, limits in self.monitoring.items():
            for limit in limits:
                if limit not in self.limits:
                    raise RuntimeError(
                        "Limit {} for program:{} does not exist".format(
                            limit, program))

        self.wait = Interval(5)

    @property
    def supervisor(self):
        return self._supervisor.supervisor

    @supervisor.setter
    def supervisor(self, value):
        self._supervisor = value

    def run(self):
        """Calls tick() with each process under Supervisor every interval"""
        while self.wait():
            for data in self.supervisor.getAllProcessInfo():
                self.tick(data)
        return self

    def tick(self, data):
        if data['pid'] != 0 and data['name'] in self.monitoring:
            for name, limit in self.monitoring[data['name']].items():
                self.limits[name](limit, data)

    def limit_memory(self, limit, data):
        rss, vms = psutil.Process(data['pid']).memory_info()
        self.log.debug(
            '%s is using %ib of %ib RSS (%2f%%)',
            data['name'], rss, limit, percentage(rss, limit))
        if rss > limit:
            self.log.warning('Restarting program:%s', data['name'])
            self.supervisor.stopProcess(data['name'])
            self.supervisor.startProcess(data['name'])
