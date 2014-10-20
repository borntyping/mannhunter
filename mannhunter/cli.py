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
@click.option(
    '-s', '--stats', is_flag=True,
    help="Prints out some mannhunter stats, does not run the daemon.")
def main(config, host, port, loglevel, stats):
    logging.basicConfig(
        level=getattr(logging, loglevel.upper()),
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    m = mannhunter.core.Mannhunter.configure(config, host=host, port=port)

    if stats:
        for service in m.stats():
            if service['mem_limit'] is not None:
                print "{0} {1} / {2}  ({3:.2%})".format(
                    service['name'],
                    mannhunter.core.sizeof_fmt(service['mem_used']),
                    mannhunter.core.sizeof_fmt(service['mem_limit']),
                    float(service['mem_used']) / float(service['mem_limit']))

        return 0
    else:
        return m.run()
