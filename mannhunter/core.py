"""Main Mannhunter class and utilities"""

from __future__ import print_function

import logging
import time
import os

import psutil
import riemann_client.client
import riemann_client.transport
import supervisor.childutils
import supervisor.datatypes


def percentage(x, y):
    return float(x) / float(y) * 100


class Interval(object):
    """Sleeps for the time since the interval was last reset when called"""

    def __init__(self, interval):
        self.interval = interval

    def __enter__(self):
        self.last = time.time()
        return self

    def __exit__(self, *exc_info):
        time.sleep(self.interval - (time.time() - self.last))
        self.last = time.time()
        return True


class Mannhunter(object):
    def __init__(self, host, port, timeout=5, interval=5):
        self.log = logging.getLogger('mannhunter')
        self.log.info("I'm going to stop you, now.")
        self.supervisor = supervisor.childutils.getRPCInterface(os.environ)
        self.riemann = riemann_client.client.Client(
            riemann_client.transport.TCPTransport(host, port, timeout))

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

        self.interval = Interval(5)

    @property
    def supervisor(self):
        return self._supervisor.supervisor

    @supervisor.setter
    def supervisor(self, value):
        self._supervisor = value

    def run(self):
        """Calls tick() with each process under Supervisor every interval"""
        with self.riemann:
            while True:
                with self.interval:
                    for data in self.supervisor.getAllProcessInfo():
                        self.tick(data)
                    # self.riemann.flush()
        return self

    def tick(self, data):
        if data['pid'] != 0 and data['name'] in self.monitoring:
            for name, limit in self.monitoring[data['name']].items():
                self.limits[name](limit, data)

    def limit_memory(self, limit, data):
        rss, vms = psutil.Process(data['pid']).memory_info()
        usage = percentage(rss, limit)
        description = '{0} is using {1:d}b of {2:d}b RSS ({3:2f}%)'.format(
            data['name'], rss, limit, usage)
        self.log.debug(description)
        self.riemann.event(
            service='process:{0}:limits:mem'.format(data['name']),
            state='ok' if usage < 100 else 'critical',
            metric_f=usage, description=description)
        if rss > limit:
            self.log.warning('Restarting program:%s', data['name'])
            self.supervisor.stopProcess(data['name'])
            self.supervisor.startProcess(data['name'])
