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
def main(config, host, port):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    return mannhunter.core.Mannhunter.configure(
        config, host=host, port=port).run()
