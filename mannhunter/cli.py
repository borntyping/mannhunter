"""Command line entry point to Mannhunter"""

from __future__ import print_function

import logging
import time

import click

import mannhunter


class Interval(object):
    def __init__(self, interval):
        self.interval = interval

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *exc_info):
        time.sleep(self.interval - (time.time() - self.start))


class Mannhunter(object):
    def __init__(self):
        self.log = logging.getLogger('mannhunter')

    def do_thing(self):
        self.log.info("Started doing a thing")
        time.sleep(0.5)
        self.log.info("Stopped doing a thing")

    def run(self):
        while True:
            with Interval(5):
                self.do_thing()
        return self


@click.command()
@click.version_option(version=mannhunter.__version__)
def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    return Mannhunter().run()
