#!/usr/bin/python3
#
# Copyright (C) 2021 Jacob Schultz Andersen schultz.jacob@gmail.com
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import re
import sys
import signal
import argparse
import tempfile
import oocd_tool.rpc_client as rpc

from time import sleep
from configparser import ConfigParser, ExtendedInterpolation
from pathlib import PurePath, Path
from oocd_tool.util import *

def signal_handler(sig, frame):
    pass


def error_exit(message):
    sys.stderr.write(message + '\n')
    sys.exit(1)


def parse_config(file, section):
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.read(file)
    if not parser.has_section(section):
        raise ConfigException("Error: invalid section: {}".format(section))
    items = parser.items(section)
    for node in items:
        yield node


def translate(nodes, **options):
    class Res:
        has_tmpfile = False
        nodes = {}
        files = {}

    tmpcnt = 0
    for key, value in nodes:
        value = re.sub(r'@CONFIG@', options['config'], value)
        value = re.sub(r'@ELFFILE@', options['elf'], value)
        if value.find('@TMPFILE@') != -1:
            if tmpcnt == 0:
                Res.tmpfile = tempfile.NamedTemporaryFile()
                value = re.sub(r'@TMPFILE@', Res.tmpfile.name, value)
                Res.has_tmpfile = True
                tmpcnt += 1
            elif tmpcnt == 1:
                value = re.sub(r'@TMPFILE@', Res.tmpfile.name, value)
            else:
                raise ConfigException("Error: @TMPFILE@ may only be used in pairs once.")
        if value.find('@FCPU@') != -1:
            if options['fcpu'] == None: raise ConfigException('Error: --fcpu is missing.')
            value = re.sub(r'@FCPU@', str(options['fcpu']), value)
        if re.match('config\..+', key):
            Res.files['@{}@'.format(key)] = value
        else:
            Res.nodes[key] = value

    # Append path to config keys there only contains filename
    path = Res.nodes['config_path'] if 'config_path' in Res.nodes else options['config_path']
    for key, file in Res.files.items():
        Res.files[key] = file if file.count('/') != 0 else str(PurePath(PurePath(path), PurePath(file)))

    # Replace @config@ tags with real path
    expr = re.compile(r'@config\.[a-z0-9]+@')
    for key, item in Res.nodes.items():
        tags = expr.findall(item)
        for tag in tags:
            item = item.replace(tag, Res.files[tag])
        Res.nodes[key] = item
    return Res


def check_mandatory_keys(config, key_list):
    for key in key_list:
        if not key in config:
            if not (key == 'openocd_executable' and 'openocd_remote' in config):
                raise ConfigException('Error: missing configuration entry: {}'.format(key))


def check_executable(file):
    import shutil
    if shutil.which(file) == None:
        raise ConfigException('Error: executable not found: {}'.format(file))


def validate_configuration(config, section):
    if not 'mode' in config or not config['mode'] in ['gdb_openocd', 'openocd', 'gdb']:
        raise ConfigException('Error: mode not specified in section: [{}]'.format(section))
    if config['mode'] == 'gdb':
        check_mandatory_keys(config, ['gdb_executable', 'gdb_args'])
        check_executable(config['gdb_executable'])
    if config['mode'] != 'gdb':
        check_mandatory_keys(config, ['openocd_executable', 'openocd_args'])
        if 'openocd_remote' not in config:
            check_executable(config['openocd_executable'])


def validate_files(files):
    for key, file in files.items():
        if not Path(file).is_file():
            raise ConfigException('Error: file not found: {}'.format(file))


def create_default_config():
    path = Path(Path.home(), ".oocd-tool")
    if (not path.exists()):
        from .configs import create_default_config
        create_default_config(path)

def default_config_file():
    path = Path(Path(Path.home(), ".oocd-tool"), Path('oocd-tool.cfg'))
    if (not path.exists()):
        raise ConfigException("Error: default config '{}' not found.".format(path))
    return path


def raise_if_running(filename):
    running, pid = is_process_running(filename)
    if running: raise ProcessException('Error: openocd is already runnning with pid: {}'.format(pid))


def run_openocd_remote(hostname, args):
    n = args.find(' ')
    cmd = args if n == -1 else args[0 : n]
    print(n, cmd, args)
    if cmd == 'program' and n != -1:
        rpc.program_device(hostname, args[len(cmd) + 1:])
    elif cmd == 'reset':
        rpc.reset_device(hostname)
    elif cmd == 'logstream' and n != -1:
        rpc.log_stream_create(hostname, args[len(cmd) + 1:])
    else:
        raise ConfigException('Error: invalid ocdrpc mode: {}'.format(args))


def execute(cfg):
    sproc = None
    ocd = None
    try:
        if 'spawn_process' in cfg:
            proc = BackgroundProcess(cfg['spawn_process'], '', True)
        if cfg['mode'] == 'gdb_openocd':
            signal.signal(signal.SIGINT, signal_handler)
            raise_if_running(cfg['openocd_executable'])
            ocd = BackgroundProcess(cfg['openocd_executable'], cfg['openocd_args'], False)
            sleep(0.1)
            if not ocd.is_running():
                raise ProcessException('Error: openocd prematurely exited with code: {}'.format(ocd.returncode()))
            BlockingProcess(cfg['gdb_executable'], cfg['gdb_args'])
            ocd.terminate()
        elif cfg['mode'] == 'openocd':
            if 'openocd_remote' in cfg:
                run_openocd_remote(cfg['openocd_remote'], cfg['openocd_args'])
            else:
                raise_if_running(cfg['openocd_executable'])
                ocd = BackgroundProcess(cfg['openocd_executable'], cfg['openocd_args'], True)
                ocd.wait()
        elif cfg['mode'] == 'log':
            pass #TODO
        elif cfg['mode'] == 'gdb':
            if 'openocd_remote' in cfg:
                with rpc.RemoteDebug(cfg['openocd_remote']):
                    BlockingProcess(cfg['gdb_executable'], cfg['gdb_args'])
            else:
                BlockingProcess(cfg['gdb_executable'], cfg['gdb_args'])
    except ProcessException:
        terminate(sproc)
        terminate(ocd)
        raise
    terminate(sproc)
    terminate(ocd)

def main():
    parser = argparse.ArgumentParser(description = 'oocd-tool')
    parser.add_argument(dest = 'section', nargs = '?', metavar='SECTION', help = 'section in config file to run')
    parser.add_argument(dest = 'source', nargs = '?', metavar='ELF', help = 'target elf file')
    parser.add_argument('-c', dest = 'config', nargs = '?', metavar='CONFIG', help = 'config file')
    parser.add_argument('--fcpu', action='store', type=int, metavar='FREQ', help = 'cpu clock (used with itm logging)')
    parser.add_argument('-d', action='store_true', help = 'dry run')
    args = parser.parse_args()

    create_default_config()
    if args.config == None:
        args.config = default_config_file()

    if args.source == None or args.config == None or args.section == None:
        error_exit("Invalid or missing parameres..")
    if not Path(args.source).is_file():
        error_exit("ELF file does not exists")
    if not Path(args.config).is_file():
        error_exit("Error cannot open config file: {}".format(args.config))

    # regex fails with windows path's. as_posix() used as workarround
    config_path = PurePath(args.config).parent.as_posix()

    pc = parse_config(args.config, args.section)
    result = translate(pc, config=config_path, elf=args.source, fcpu=args.fcpu)
    cfg = result.nodes

    # dry run
    if args.d:
        print('')
        if cfg['mode'] in ['gdb_openocd', 'gdb']: print('gdb: {} {}\n'.format(cfg['gdb_executable'], cfg['gdb_args']))
        if cfg['mode'] in ['gdb_openocd', 'openocd']: print('openocd: {} {}\n'.format(cfg['openocd_executable'], cfg['openocd_args']))
        if 'spawn_process' in cfg: print('spawn: {}\n'.format(cfg['spawn_process']))
        sys.exit(0)

    validate_configuration(cfg, args.section)
    validate_files(result.files)
    execute(cfg)


if __name__ == "__main__":
    main()

