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
@click.argument(
    'host', type=click.STRING, required=False, envvar='RIEMANN_HOST')
@click.argument(
    'port', type=click.INT, required=False, envvar='RIEMANN_PORT')
def main(config, host, port):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    return mannhunter.core.Mannhunter.configure(
        config, host=host, port=port).run()
