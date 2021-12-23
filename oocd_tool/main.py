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
import oocd_tool.rpc_client as rpc_client
from time import sleep
from configparser import ConfigParser, ExtendedInterpolation
from pathlib import PurePath, Path
from oocd_tool.process import *


def signal_handler(_sig, _frame):
    pass


def error_exit(message):
    sys.stderr.write(message + '\n')
    sys.exit(1)


def get_config_value(config, key, message):
    if key not in config:
        raise ConfigException(message)
    return config.nodes[key]


def parse_config(file, section):
    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.read(file)
    if not parser.has_section(section):
        raise ConfigException(f"Error: invalid section: {section}")
    items = parser.items(section)
    for node in items:
        yield node


def translate(nodes, **options):
    class Result:
        def __init__(self):
            self.has_tmpfile = False
            self.nodes = {}
            self.files = {}

        def __getattr__(self, name):
            try:
                cfg = self.nodes[name]
            except KeyError as e:
                raise AttributeError(e)
            return cfg

        def __iter__(self):
            return iter(self.nodes)

    res = Result()

    counter = 0
    for key, value in nodes:
        value = re.sub(r'@CONFIG@', options['config'], value)
        value = re.sub(r'@ELFFILE@', options['elf'], value)
        if value.find('@TMPFILE@') != -1:
            if counter == 0:
                res.tmpfile = tempfile.NamedTemporaryFile()
                value = re.sub(r'@TMPFILE@', res.tmpfile.name, value)
                res.has_tmpfile = True
                counter += 1
            elif counter == 1:
                value = re.sub(r'@TMPFILE@', res.tmpfile.name, value)
            else:
                raise ConfigException("Error: @TMPFILE@ may only be used in pairs once.")
        if value.find('@FCPU@') != -1:
            if options['fcpu'] is None:
                raise ConfigException('Error: --fcpu is missing.')
            value = re.sub(r'@FCPU@', str(options['fcpu']), value)
        if re.match(r'config\..+', key):
            res.files[f'@{key}@'] = value
        else:
            res.nodes[key] = value

    # Append path to config keys there only contains filename
    path = res.nodes['config_path'] if 'config_path' in res.nodes else options['config_path']
    for key, file in res.files.items():
        res.files[key] = file if file.count('/') != 0 else str(PurePath(PurePath(path), PurePath(file)))

    # Replace @config@ tags with real path
    expr = re.compile(r'@config\.[a-z0-9]+@')
    for key, item in res.nodes.items():
        tags = expr.findall(item)
        for tag in tags:
            item = item.replace(tag, res.files[tag])
        res.nodes[key] = item
    return res


def check_mandatory_keys(config, key_list):
    for key in key_list:
        if key not in config:
            if not (key == 'openocd_executable' and 'openocd_remote' in config):
                raise ConfigException(f'Error: missing configuration entry: {key}')


def check_executable(file):
    import shutil
    if shutil.which(file) is None:
        raise ConfigException(f'Error: executable not found: {file}')


def validate_configuration(config, section):
    if 'mode' not in config or config.mode not in ['gdb_openocd', 'openocd', 'gdb']:
        raise ConfigException(f'Error: mode not specified in section: [{section}]')
    if config.mode == 'gdb':
        check_mandatory_keys(config, ['gdb_executable', 'gdb_args'])
        check_executable(config['gdb_executable'])
    if config.mode != 'gdb':
        check_mandatory_keys(config, ['openocd_executable', 'openocd_args'])
        if 'openocd_remote' not in config:
            check_executable(config.openocd_executable)


def validate_files(files):
    for key, file in files.items():
        if not Path(file).is_file():
            raise ConfigException(f'Error: file not found: {file}')


def create_default_config():
    path = Path(Path.home(), ".oocd-tool")
    if not path.exists():
        from .configs import create_default_config
        create_default_config(path)


def default_config_file():
    path = Path(Path(Path.home(), ".oocd-tool"), Path('oocd-tool.cfg'))
    if not path.exists():
        raise ConfigException(f"Error: default config '{path}' not found.")
    return path


def raise_if_running(filename):
    running, pid = is_process_running(filename)
    if running:
        raise ProcessException(f'Error: openocd is already running with pid: {pid}')


def run_openocd_remote(rpc, args):
    n = args.find(' ')
    cmd = args if n == -1 else args[0: n]
    if cmd == 'program' and n != -1:
        stream = rpc.program_device(args[len(cmd) + 1:])
        for line in stream:
            print(line)
    elif cmd == 'reset':
        stream = rpc.reset_device()
        for line in stream:
            print(line)
    elif cmd == 'logstream' and n != -1:
        stream = rpc.log_stream_create(args[len(cmd) + 1:])
        for line in stream:
            print(line)
    else:
        raise ConfigException(f'Error: invalid rpc mode: {args}')


class LocalExecuteInterface:
    def __init__(self):
        self.ocd = None

    def spawn_process(self, cfg):
        BackgroundProcess(cfg.spawn_process, '', True)

    def debug_spawned_openocd(self, cfg):
        raise_if_running(cfg.openocd_executable)
        self.ocd = BackgroundProcess(cfg.openocd_executable, cfg.openocd_args, False)
        sleep(0.1)
        if not self.ocd.is_running():
            raise ProcessException(f'Error: openocd prematurely exited with code: {self.ocd.returncode()}')
        BlockingProcess(cfg.gdb_executable, cfg.gdb_args)
        self.ocd.terminate()

    def debug(self, cfg):
        raise_if_running(cfg.openocd_executable)
        BlockingProcess(cfg.gdb_executable, cfg.gdb_args)

    def openocd_only(self, cfg):
        raise_if_running(cfg.openocd_executable)
        self.ocd = BackgroundProcess(cfg.openocd_executable, cfg.openocd_args, True)
        self.ocd.wait()
        pass

    def __del__(self):
        terminate(self.ocd)


class RemoteExecuteInterface:
    def __init__(self, channel, auth_key):
        self.channel = channel
        self.auth_key = auth_key

    def spawn_process(self):
        # TODO
        raise ConfigException("Not implemented yet.")

    def debug_spawned_openocd(self):
        raise ConfigException("Invalid mode configured.")

    def debug(self, cfg):
        rpc = rpc_client.ClientChannel(cfg.openocd_remote, self.channel, self.auth_key)
        with rpc.debug_device():
            BlockingProcess(cfg.gdb_executable, cfg.gdb_args)

    def openocd_only(self, cfg):
        rpc = rpc_client.ClientChannel(cfg.openocd_remote, self.channel, self.auth_key)
        run_openocd_remote(rpc, cfg.openocd_args)


def execute(cfg):
    auth_key = ""
    channel = rpc_client.secure_channel
    if 'openocd_remote' in cfg:
        if 'tls_mode' in cfg and cfg.tls_mode == 'disabled':
            channel = rpc_client.insecure_channel
        else:
            auth_key = get_config_value(cfg, 'cert_auth_key', "Error: 'cert_signature_key' not specified.")
        interface = RemoteExecuteInterface(channel, auth_key)
    else:
        interface = LocalExecuteInterface()
    if 'spawn_process' in cfg:
        interface.spawn_process(cfg)
    if cfg.mode == 'gdb_openocd':
        signal.signal(signal.SIGINT, signal_handler)
        interface.debug_spawned_openocd(cfg)
    elif cfg.mode == 'openocd':
        interface.openocd_only(cfg)
    elif cfg.mode == 'log':
        # TODO
        raise ConfigException("Not implemented yet.")
    elif cfg.mode == 'gdb':
        signal.signal(signal.SIGINT, signal_handler)
        interface.debug(cfg)


def main():
    parser = argparse.ArgumentParser(description='oocd-tool')
    parser.add_argument(dest='section', nargs='?', metavar='SECTION', help='section in config file to run')
    parser.add_argument(dest='source', nargs='?', metavar='ELF', help='target elf file')
    parser.add_argument('-c', dest='config', nargs='?', metavar='CONFIG', help='config file')
    parser.add_argument('--fcpu', action='store', type=int, metavar='FREQ', help='cpu clock (used with itm logging)')
    parser.add_argument('-d', action='store_true', help='dry run')
    args = parser.parse_args()

    create_default_config()
    if args.config is None:
        args.config = default_config_file()
    if args.section is None:
        error_exit("Section not specified.")
    if args.source is not None and not Path(args.source).is_file():
        error_exit("ELF file does not exists.")
    if not Path(args.config).is_file():
        error_exit(f"Error cannot open config file: {args.config}.")
    if args.source is None:
        args.source = ''

    # regex fails with windows path's. as_posix() used as workaround
    config_path = PurePath(args.config).parent.as_posix()

    pc = parse_config(args.config, args.section)
    cfg = translate(pc, config=config_path, elf=args.source, fcpu=args.fcpu)

    # dry run
    if args.d:
        print('')
        if cfg.mode in ['gdb_openocd', 'gdb']:
            print(f'gdb: {cfg.gdb_executable} {cfg.gdb_args}\n')
        if cfg.mode in ['gdb_openocd', 'openocd']:
            print(f'openocd: {cfg.openocd_executable} {cfg.openocd_args}\n')
        if 'spawn_process' in cfg.nodes:
            print(f'spawn: {cfg.spawn_process}\n')
        sys.exit(0)

    validate_configuration(cfg, args.section)
    validate_files(cfg.files)
    rpc_client.load_certificates(cfg)
    execute(cfg)


if __name__ == "__main__":
    main()
