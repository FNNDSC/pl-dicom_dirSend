#!/usr/bin/env python

from pathlib import Path
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter
from jobController import jobber
from chris_plugin import chris_plugin, PathMapper
from    loguru              import logger
from    datetime            import datetime
import sys
import os
LOG             = logger.debug

logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> │ "
    "<level>{level: <5}</level> │ "
    "<yellow>{name: >28}</yellow>::"
    "<cyan>{function: <30}</cyan> @"
    "<cyan>{line: <4}</cyan> ║ "
    "<level>{message}</level>"
)
logger.remove()
logger.opt(colors = True)
logger.add(sys.stderr, format=logger_format)

__version__ = '1.2.1'

DISPLAY_TITLE = r"""
       _           _ _                          _ _      _____                _ 
      | |         | (_)                        | (_)    /  ___|              | |
 _ __ | |______ __| |_  ___ ___  _ __ ___    __| |_ _ __\ `--.  ___ _ __   __| |
| '_ \| |______/ _` | |/ __/ _ \| '_ ` _ \  / _` | | '__|`--. \/ _ \ '_ \ / _` |
| |_) | |     | (_| | | (_| (_) | | | | | || (_| | | |  /\__/ /  __/ | | | (_| |
| .__/|_|      \__,_|_|\___\___/|_| |_| |_| \__,_|_|_|  \____/ \___|_| |_|\__,_|
| |                                     ______                                  
|_|   
""" + "\t\t -- version " + __version__ + " --\n\n"


parser = ArgumentParser(description='A ChRIS plugin to send DICOMs to a remote PACS store',
                        formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument('-f', '--fileFilter', default='dcm', type=str,
                    help='input file filter glob')
parser.add_argument('-n', '--host', default='0.0.0.0', type=str,
                    help='Host IP')
parser.add_argument('-p', '--port', default='4242', type=str,
                    help='Host port')
parser.add_argument('-a', '--aeTitle', default='ChRIS', type=str,
                    help='my AE title')
parser.add_argument('-c', '--calledAETitle', default='CHRISLOCAL', type=str,
                    help='called AE title of peer')
parser.add_argument('-s', '--singleInstanceMode', default=False, action="store_true",
                    help='called AE title of peer')
parser.add_argument('-V', '--version', action='version',
                    version=f'%(prog)s {__version__}')


def preamble_show(options) -> None:
    """
    Just show some preamble "noise" in the output terminal
    """

    LOG(DISPLAY_TITLE)

    LOG("plugin arguments...")
    for k, v in options.__dict__.items():
        LOG("%25s:  [%s]" % (k, v))
    LOG("")

    LOG("base environment...")
    for k, v in os.environ.items():
        LOG("%25s:  [%s]" % (k, v))
    LOG("")


# The main function of this *ChRIS* plugin is denoted by this ``@chris_plugin`` "decorator."
# Some metadata about the plugin is specified here. There is more metadata specified in setup.py.
#
# documentation: https://fnndsc.github.io/chris_plugin/chris_plugin.html#chris_plugin
@chris_plugin(
    parser=parser,
    title='A ChRIS plugin to send DICOMs to a remote PACS store',
    category='',                 # ref. https://chrisstore.co/plugins
    min_memory_limit='100Mi',    # supported units: Mi, Gi
    min_cpu_limit='1000m',       # millicores, e.g. "1000m" = 1 CPU core
    min_gpu_limit=0              # set min_gpu_limit=1 to enable GPU
)
def main(options: Namespace, inputdir: Path, outputdir: Path):
    """
    *ChRIS* plugins usually have two positional arguments: an **input directory** containing
    input files and an **output directory** where to write output files. Command-line arguments
    are passed to this main method implicitly when ``main()`` is called below without parameters.

    :param options: non-positional arguments parsed by the parser given to @chris_plugin
    :param inputdir: directory containing (read-only) input files
    :param outputdir: directory where to write output files
    """

    preamble_show(options)

    # Typically it's easier to think of programs as operating on individual files
    # rather than directories. The helper functions provided by a ``PathMapper``
    # object make it easy to discover input files and write to output files inside
    # the given paths.
    #
    # Refer to the documentation for more options, examples, and advanced uses e.g.
    # adding a progress bar and parallelism.
    # lets create a log file in the o/p directory first
    log_file = os.path.join(options.outputdir, 'terminal.log')
    logger.add(log_file)
    shell = jobber({'verbosity': 1, 'noJobLogging': True})

    base_cmd = build_dcmsend_base(options)
    mapper = PathMapper.file_mapper(
        inputdir,
        outputdir,
        glob=f"**/*.{options.fileFilter}",
        fail_if_empty=False
    )

    # Send a single DICOM per association
    if options.singleInstanceMode:
        for input_file, _ in mapper:
            LOG(f"Sending input file: ---->{input_file.name}<---- to {options.calledAETitle}")

            cmd = f"{base_cmd} {input_file}"
            try:
                run_dcmsend(shell, cmd)
            except Exception as e:
                continue

    # Future goals: 1) Implement max PDU and disable-host-lookup
    else:
        LOG(f"Sending: ---->{len(mapper)} DICOMs<---- to {options.calledAETitle}")
        cmd = (
            f"{base_cmd} "
            f"-q +r +sd +sp *{options.fileFilter} "
            f"{inputdir}"
        )

        run_dcmsend(shell, cmd)

def run_dcmsend(shell,cmd: str):
    """Execute dcmsend command and handle logging/errors."""
    d_response = shell.job_run(cmd)

    LOG(f"Command: {d_response['cmd']}")

    if d_response["returncode"]:
        LOG(f"Error: {d_response['stderr']}")
        raise RuntimeError(d_response["stderr"])

    LOG("Response: Success\n")


def build_dcmsend_base(options):
    """Base dcmsend command."""
    return (
        f"dcmsend "
        f"-aet {options.aeTitle} "
        f"-aec {options.calledAETitle} "
        f"{options.host} "
        f"{options.port}"
    )



if __name__ == '__main__':
    main()
