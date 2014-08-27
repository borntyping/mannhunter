"""Main Mannhunter class and utilities"""

from __future__ import print_function, division

import ConfigParser
import glob
import logging
import re
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


class MannhunterConfigParser(ConfigParser.RawConfigParser):
    def __getitem__(self, section):
        return dict([(k, self.get(section, k)) for k in self.options(section)])

    def read_includes(self, cwd=os.curdir):
        if self.has_section('include'):
            if not self.has_option('include', 'files'):
                raise ValueError("[include] section must define files=")

            pattern = os.path.join(cwd, self.get('include', 'files'))
            for filename in glob.glob(pattern):
                self.read(filename)


class Mannhunter(object):
    @staticmethod
    def parse_memory(limit):
        """Parses a string describing memory allowance

        Strings ending with with ``gb``, ``mb`` or ``kb`` are parsed as byte
        sizes, strings ending with ``%`` are parsed as a percentage of the
        systems memory. All other strings are parsed as integers representing a
        byte value.

        :param str limit: The memory limit to parse
        :raises RuntimeError: Memory limits must be above 0
        """
        if re.match('\d+(gb|mb|kb)', limit, flags=re.IGNORECASE):
            bytes = supervisor.datatypes.byte_size(limit)
        elif re.match('\d+%', limit):
            modifier = int(limit[:-1]) / 100
            bytes = int(modifier * psutil.virtual_memory().total)
        else:
            bytes = int(limit)

        if bytes <= 0:
            raise RuntimeError("Memory limit must be above 0")

        return bytes

    @classmethod
    def configure(cls, filename=None, **overrides):
        """Configures a Mannhunter instance based on a file(s)"""
        config = MannhunterConfigParser()

        config.add_section('mannhunter')
        config.set('mannhunter', 'host', 'localhost')
        config.set('mannhunter', 'port', 5555)

        if filename is not None:
            config.read(filename)
            config.read_includes(cwd=os.path.dirname(filename))

        for k, v in overrides.items():
            if v is not None:
                config.set('mannhunter', k, v)

        instance = cls(**config['mannhunter'])

        for section in config.sections():
            if section.startswith('program:'):
                instance.add_program(name=section[8:], **config[section])

        for name, limit in instance.limits.items():
            logging.getLogger('mannhunter.config').debug(
                "Program '%s' has a configured limit of %sb", name, limit)

        return instance

    def __init__(self, host, port, timeout=5, interval=5, default_limit='80%'):
        self.log = logging.getLogger('mannhunter')
        self.log.info("I'm going to stop you, now.")

        #: Supervisor RPC connection, used to collect program information
        self.supervisor = supervisor.childutils.getRPCInterface(os.environ)

        #: Riemann client, used to send limit metrics
        self.riemann = riemann_client.client.Client(
            riemann_client.transport.TCPTransport(host, port, timeout))

        #: How often to scan the processes
        self.interval = Interval(5)

        #: The programs that will be monitored (``name -> limits``)
        self.limits = {}
        self.default_limit = self.parse_memory(default_limit)

        assert all(l >= 0 for l in self.limits.values())
        assert self.default_limit >= 0

        self.log.info(
            "Using a default limit of %sb (%s) every %ss",
            self.default_limit, default_limit, self.interval.interval)

    def add_program(self, name, memory='80%'):
        self.limits[name] = self.parse_memory(memory)

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
            if data['pid'] != 0:
                self.limit_memory(data)

    def limit_memory(self, data):
        """Restart a process if it has used more than it's memory limit"""
        rss, vms = psutil.Process(data['pid']).memory_info()
        limit = self.limits.get(data['name'], self.default_limit)
        usage = percentage(rss, limit)
        self.riemann_event(
            service='process:{0}:limits:mem'.format(data['name']),
            state='ok' if usage < 100 else 'critical', metric_f=usage,
            description='{0} is using {1}b of {2}b RSS ({3:05.2f}%)'.format(
                data['name'], rss, limit, usage))
        if rss > limit:
            self.restart_process(data['name'])

    def restart_process(self, name):
        """Start and stop a process running under supervisor"""
        self.log.warning('Restarting program:%s', name)
        self.supervisor.stopProcess(name)
        self.supervisor.startProcess(name)

    def riemann_event(self, **event):
        """Send an event to Riemann and log the description"""
        self.riemann.event(**event)
        self.log.debug(event.get('description', "Sent an event to Riemann"))
