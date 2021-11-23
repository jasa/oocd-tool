#!/usr/bin/python
#
# Copyright (C) 2021 Jacob Schultz Andersen schultz.jacob@gmail.com
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import re
import sys, os
import signal
import argparse
import tempfile
from .util import *

from configparser import ConfigParser, ExtendedInterpolation

from pathlib import PurePath, Path

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

    for key, value in nodes:
        value = re.sub(r'@CONFIG@', options['config'], value)
        value = re.sub(r'@ELFFILE@', options['elf'], value)
        if value.find('@TMPFILE@') != -1:
            Res.tmpfile = tempfile.NamedTemporaryFile()
            Res.has_tmpfile = True
            value = re.sub(r'@TMPFILE@', Res.tmpfile.name, value)
        if value.find('@FCPU@') != -1:
            if options['fcpu'] == None: raise ConfigException('Error: --fcpu is missing')
            value = re.sub(r'@FCPU@', str(options['fcpu']), value)
        if re.match('config\..+', key):
            Res.files['@{}@'.format(key)] = value
        else:
            Res.nodes[key] = value

    path = Res.nodes['config_path'] if 'config_path' in Res.nodes else options['config_path']
    for key, file in Res.files.items():
        Res.files[key] = file if file.count('/') != 0 else str(PurePath(PurePath(path), PurePath(file)))

    expr = re.compile(r'@config\.[a-z0-9]+@')
    for key, item in Res.nodes.items():
        tags = expr.findall(item)
        for tag in tags:
            item = item.replace(tag, Res.files[tag])
        Res.nodes[key] = item
    return Res

def check_mandatory_keys(config, key_list):
    for key in key_list:
        if not key in config: raise ConfigException('Error: missing configuration entry: {}'.format(key))

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
        check_executable(config['openocd_executable'])

def validate_files(files):
    for key, file in files.items():
        if not Path(file).is_file():
            raise ConfigException('Error: file not found: {}'.format(file))

def default_config_file():
    path = Path(Path.home(), ".openocd-tool")
    if (not path.exists()):
        from .configs import create_default_config
        create_default_config(path)
    path = Path(path, Path('openocd-tool.cfg'))
    if (not path.exists()):
        raise ConfigException("Error: default config '{}' not found.".format(path))
    print(path)
    return path

def main():
    parser = argparse.ArgumentParser(description = 'openocd-tool')
    parser.add_argument(dest = 'section', nargs = '?', metavar='SECTION', help = 'section in config file to run')
    parser.add_argument(dest = 'source', nargs = '?', metavar='ELF', help = 'target elf file')
    parser.add_argument('-c', dest = 'config', nargs = '?', metavar='CONFIG', help = 'config file')
    parser.add_argument('--fcpu', action='store', type=int, metavar='FREQ', help = 'cpu clock (used with itm logging)')
    parser.add_argument('-d', action='store_true', help = 'dry run')
    args = parser.parse_args()

    if args.config == None:
        args.config = default_config_file()

    if args.source == None or args.config == None or args.section == None:
        error_exit("Invalid or missing parameres..")
    if not Path(args.source).is_file():
        error_exit("ELF file does not exists")
    if not Path(args.config).is_file():
        error_exit("Error cannot open config file: {}".format(args.config))
    config_path = os.path.dirname(args.config)

    pc = parse_config(args.config, args.section)
    result = translate(pc, config=config_path, elf=args.source, fcpu=args.fcpu)
    cfg = result.nodes

    validate_configuration(cfg, args.section)
    validate_files(result.files)

    # dry run
    if args.d:
        if cfg['mode'] in ['gdb_openocd', 'gdb']: print('\n{} {}\n'.format(cfg['gdb_executable'], cfg['gdb_args']))
        if cfg['mode'] in ['gdb_openocd', 'openocd']: print('{} {}\n'.format(cfg['openocd_executable'], cfg['openocd_args']))
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    if cfg['mode'] == 'gdb_openocd':
        ocd = OpenOCD_Run('{} {}'.format(cfg['openocd_executable'], cfg['openocd_args']), False)
        try:
            GDB_Run('{} {}'.format(cfg['gdb_executable'], cfg['gdb_args']))
        except GDBException as e:
            ocd.terminate()
            raise e
        ocd.terminate()
    elif cfg['mode'] == 'openocd':
        ocd = OpenOCD_Run('{} {}'.format(cfg['openocd_executable'], cfg['openocd_args']), True)
        ocd.wait()
    elif cfg['mode'] == 'log':
        pass #TODO
    elif cfg['mode'] == 'gdb':
        GDB_Run('{} {}'.format(cfg['gdb_executable'], cfg['gdb_args']))
    else:
        error_exit('Invalid mode: {}'.format(cfg['mode']))