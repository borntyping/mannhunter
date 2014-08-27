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
                # Wait the rest of the interval before continuing
                with self.interval:
                    self.tick()
        return self

    def tick(self):
        """Run the limit functions associated with each process"""
        for data in self.supervisor.getAllProcessInfo():
            if data['pid'] != 0 and data['name'] in self.monitoring:
                for name, limit in self.monitoring[data['name']].items():
                    self.limits[name](limit, data)

    def limit_memory(self, limit, data):
        """Restart a process if it has used more than it's memory limit"""
        rss, vms = psutil.Process(data['pid']).memory_info()
        usage = percentage(rss, limit)
        self.riemann_event(
            service='process:{0}:limits:mem'.format(data['name']),
            state='ok' if usage < 100 else 'critical', metric_f=usage,
            description='{0} is using {1:d}b of {2:d}b RSS ({3:2f}%)'.format(
                data['name'], rss, limit, usage))
        if rss > limit:
            self.restart_process(data['name'])

    def restart_process(self, name):
        """Start and stop a process running under supervisor"""
        self.log.warning('Restarting program:%s', name)
        self.supervisor.stopProcess(name)
        self.supervisor.startProcess(name)

    def riemann_event(self, **event):
        self.riemann.event(**event)
        self.log.debug(event.get('description', "Sent an event to Riemann"))
