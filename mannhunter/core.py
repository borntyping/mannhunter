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


def create_riemann_client(host, port, timeout):
    """Creates a Riemann client instance, passing correct types"""
    return riemann_client.client.Client(riemann_client.transport.TCPTransport(
        str(host), int(port), float(timeout)))


def sizeof_fmt(num):
    """Formats bytes in human readable form."""
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


class Interval(object):
    """Sleeps for the time since the interval was last reset when called"""

    def __init__(self, interval):
        self.interval = interval

    def __enter__(self):
        self.last = time.time()
        return self

    def __exit__(self, *exc_info):
        interval = self.interval - (time.time() - self.last)
        if interval > 0:
            time.sleep(interval)

        self.last = time.time()
        return True


class MannhunterConfigParser(ConfigParser.RawConfigParser):
    def __getitem__(self, section):
        return dict([(k, self.get(section, k)) for k in self.options(section)])

    def read_includes(self, cwd=os.curdir):
        if self.has_section('include'):
            if not self.has_option('include', 'files'):
                raise ValueError("[include] section must define files=")

            for pattern in self.get('include', 'files').split():
                for filename in glob.glob(os.path.join(cwd, pattern)):
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
        """Configures a Mannhunter instance based on a file(s)

        Similar to supervisor, an ``[include]`` directive allows additional
        files to be included::

            [include]
            files=

        """
        config = MannhunterConfigParser()
        config.add_section('mannhunter')

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

        return instance

    def __init__(self, host=None, port=5555, timeout=5,
                 interval=5, default_limit='80%'):
        self.log = logging.getLogger('mannhunter')

        #: Supervisor RPC connection, used to collect program information
        self.supervisor = supervisor.childutils.getRPCInterface(os.environ)

        if host is not None:
            self.log.debug('Sending metrics to Riemann at %s:%s', host, port)
            self.riemann = create_riemann_client(host, port, timeout)
        else:
            self.log.debug('Not sending metrics to Riemann')
            self.riemann = None

        #: How often to scan the processes
        self.interval = Interval(5)

        #: The programs that will be monitored (``name -> limits``)
        self.limits = {}

        #: The limit to use for programs with no defined limit
        self.default_limit = self.parse_memory(default_limit)
        self._default_limit = default_limit

        # Log information about the current configuration when starting
        self.log.debug(
            "Using a default limit of %sb (%s) every %ss",
            self.default_limit, self._default_limit, self.interval.interval)

    def __enter__(self):
        if self.riemann is not None:
            self.riemann.__enter__()
        return self

    def __exit__(self, *exc_info):
        if self.riemann is not None:
            self.riemann.__exit__(*exc_info)
        return self

    @property
    def supervisor(self):
        return self._supervisor.supervisor

    @supervisor.setter
    def supervisor(self, value):
        self._supervisor = value

    def add_program(self, name, memory='80%'):
        """A a memory limit to ``limits`` using :py:func:`parse_memory`"""
        self.limits[name] = self.parse_memory(memory)
        self.log.debug("Program %s is limited to %sb", name, self.limits[name])

    def run(self):
        """Calls tick() with each process under Supervisor every interval"""
        self.log.info("I'm going to stop you, now.")
        with self:
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

    def stats(self):
        """Returns the current state of the services in supervisor."""
        def add_mem(service):
            """Adds current memory usage and limit to a service."""
            try:
                rss, vms = psutil.Process(service['pid']).memory_info()
                service['mem_used'] = rss
                service['mem_limit'] = self.limits[service['name']]
            except psutil.NoSuchProcess:
                service['mem_used'] = None
                service['mem_limit'] = None
            except KeyError:
                service['mem_limit'] = None

            return service

        return map(add_mem, self.supervisor.getAllProcessInfo())

    def restart_process(self, name):
        """Start and stop a process running under supervisor"""
        self.log.warning('Restarting program:%s', name)
        self.supervisor.stopProcess(name)
        self.supervisor.startProcess(name)

    def riemann_event(self, **event):
        """Send an event to Riemann and log the description"""
        if self.riemann:
            self.riemann.event(**event)
        self.log.debug(event.get('description', "Sent an event to Riemann"))
