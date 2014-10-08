"""Command line entry point to Mannhunter"""

import logging

import click

import mannhunter.core


@click.command()
@click.version_option(version=mannhunter.__version__)
@click.option(
    '-c', '--config',
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="A configuration file to load")
@click.option(
    '-H', '--host', envvar='RIEMANN_HOST', type=click.STRING, required=False,
    help="Riemann server hostname (optional)")
@click.option(
    '-P', '--port', envvar='RIEMANN_PORT', type=click.INT, default=5555,
    help="Riemann server port")
@click.option(
    '-l', '--loglevel', default='info',
    type=click.Choice(['info', 'warning', 'debug', 'error', 'critical']),
    help="The level to log at")
def main(config, host, port, loglevel):
    logging.basicConfig(
        level=getattr(logging, loglevel.upper()),
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    return mannhunter.core.Mannhunter.configure(
        config, host=host, port=port).run()
