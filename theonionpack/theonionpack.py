#!/usr/bin/env python
import click
import pathlib
import site

# theonionpack.py -d/-t --tor <path> --data <path>

import configparser

cwd = pathlib.Path(__file__).resolve()
cwd = cwd.parent
assert cwd.exists()

config = configparser.ConfigParser()
config.read(str(cwd / 'setup.ini'))
__title__ = config['theonionpack']['title']
__version__ = config['theonionpack']['version']
__description__ = config['theonionpack']['description']


# @click.group(chain=True, invoke_without_command=True)
@click.command()
@click.option('--debug', is_flag=True, flag_value=True,
              help='Switch on DEBUG mode.')
@click.option('--trace', is_flag=True, flag_value=True,
              help='Switch on TRACE mode (which is more verbose than DEBUG mode).')
@click.option('-t', '--tor', default='.\Tor', show_default=True,
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True,
                              resolve_path=True, allow_dash=False),
              help="Search directory for 'tor.exe'.")
@click.option('-d', '--data', default='.\Data', show_default=True,
              type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True,
                              resolve_path=True, allow_dash=False),
              help="Tor's DataDirectory.")
@click.version_option(prog_name=f'{__title__}: {__description__}',
                      version=__version__, message='%(prog)s\nVersion %(version)s')

@click.pass_context
def main(ctx, debug, trace, tor, data):

    params = {
        'debug': debug,
        'trace': trace,
        'tor': tor,
        'data': data,
        'cwd': str(cwd)
    }

    if __name__ == '__main__' or __package__ in [None, '']:
        site.addsitedir(str(cwd))
        from top.pack import Pack
    else:
        from .top.pack import Pack

    top = Pack(params)
    top.run()


if __name__ == '__main__':
    main()


__all__ = ['main']
