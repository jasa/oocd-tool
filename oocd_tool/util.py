#!/usr/bin/python
#
# Copyright (C) 2021 Jacob Schultz Andersen schultz.jacob@gmail.com
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import os
import psutil
import platform
import subprocess
from pathlib import PurePath, Path
from time import sleep

class ConfigFile:
    def __init__(self, prefix, name = ''):
        self.file = Path(Path(prefix), Path(name))
        if not self.file.is_file():
            raise Exception("File not found: {}".format(self.file))
    def __str__(self):
        return str(self.file)

class ConfigException(Exception):
    def __init__(self, message):
        self.message = message

class OpenOCDException(Exception):
    def __init__(self, message):
        self.message = message

class GDBException(Exception):
    def __init__(self, message):
        self.message = message

class OpenOCD_Run:
    def __init__(self, command, visible):
        running, pid = is_openocd_running()
        if running: raise OpenOCDException('Error: openocd is already runnning with pid: {}'.format(pid))

        kwargs = { 'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP } if 'Windows' in platform.platform() else {}

        redir = None if visible else subprocess.DEVNULL
        self.proc = subprocess.Popen(command, stderr=redir, start_new_session=True, cwd=os.getcwd(), shell=True, **kwargs)
        sleep(0.1)
        self.proc.poll()
        if self.proc.returncode != None:
            raise OpenOCDException('Error: openocd prematurely exited with code: {}'.format(self.proc.returncode))

    def wait(self):
        self.proc.communicate()
        if self.proc.returncode != 0:
            raise OpenOCDException('Error: openocd returned: {}'.format(self.proc.returncode))

    def terminate(self):
        self.proc.terminate()
        if self.proc.returncode != None and self.proc.returncode > 1:
            raise OpenOCDException('Error: openocd returned: {}'.format(self.proc.returncode))


def is_openocd_running():
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if (proc.name() == "openocd"):
                return True, proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False, 0

class GDB_Run:
    def __init__(self, command):
        proc = subprocess.run(command, cwd=os.getcwd(), shell=True)
        if proc.returncode != 0:
            raise GDBException('Error GDB returned: {}'.format(self.proc.returncode))
