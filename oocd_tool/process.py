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


class ConfigException(Exception):
    def __init__(self, message):
        self.message = message


class ProcessException(Exception):
    def __init__(self, message):
        self.message = message


class BackgroundProcess:
    def __init__(self, command, args, visible):
        self.cmd = command
        kwargs = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if 'Windows' in platform.platform() else {}
        redir = None if visible else subprocess.DEVNULL
        self._proc = subprocess.Popen(command + ' ' + args, stderr=redir, start_new_session=True, cwd=os.getcwd(),
                                      shell=True, **kwargs)

    def wait(self):
        self._proc.communicate()
        if self._proc.returncode != 0:
            raise ProcessException('Error: {} returncode: {}'.format(self.cmd, self._proc.returncode))

    def terminate(self):
        self._proc.terminate()
        if self._proc.returncode is not None and self._proc.returncode > 1:
            raise ProcessException('Error: {} returncode: {}'.format(self.cmd, self._proc.returncode))

    def is_running(self):
        return True if self._proc.poll() is None else False

    def returncode(self):
        return self._proc.returncode


class BlockingProcess:
    def __init__(self, command, args):
        self.cmd = command
        _proc = subprocess.run(command + ' ' + args, cwd=os.getcwd(), shell=True)
        if _proc.returncode != 0:
            raise ProcessException('Error: {} returncode: {}'.format(self.cmd, _proc.returncode))


def is_process_running(name):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.name() == name:
                return True, proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False, 0


def terminate(proc):
    if proc is not None:
        if proc.is_running():
            proc.terminate()
