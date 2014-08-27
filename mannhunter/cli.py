"""Command line entry point to Mannhunter"""

import logging

import click

import mannhunter.core


@click.command()
@click.version_option(version=mannhunter.__version__)
@click.argument(
    'host', type=click.STRING, default='localhost', envvar='RIEMANN_HOST')
@click.argument(
    'port', type=click.INT, default=5555, envvar='RIEMANN_PORT')
def main(host, port):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    return mannhunter.core.Mannhunter(host, port).run()
