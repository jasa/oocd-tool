#
# Copyright (C) 2021 Jacob Schultz Andersen schultz.jacob@gmail.com
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import os
import signal
import psutil
import subprocess
import logging
import platform
from time import sleep

_LOGGER = logging.getLogger(__name__)

class ConfigException(Exception):
    def __init__(self, message):
        self.message = message

def openocd_program(cmd):
    killall("openocd")
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True, cwd=os.getcwd(), shell=True)
    for ln in iter(proc.stderr.readline, ""):
        yield ln
    proc.stderr.close()
    ret = proc.wait()
    if ret:
        _LOGGER.error("openocd_program failed: '{}', returncode: {}".format(cmd, ret))
        raise subprocess.CalledProcessError(ret, cmd)

def openocd_reset_device(cmd):
    killall("openocd")
    proc = subprocess.run(cmd, cwd=os.getcwd(), shell=True)
    if proc.returncode != 0:
        _LOGGER.error("openocd_reset_device failed: '{}', returncode: {}".format(cmd, proc.returncode))
        raise subprocess.CalledProcessError(proc.returncode, cmd)

def openocd_start_debug(cmd):
    killall("openocd")
    proc = subprocess.Popen(cmd, cwd=os.getcwd(), shell=True)
    sleep(0.1)
    ret = proc.poll()
    if ret != None:
        _LOGGER.error("openocd_start_debug failed: '{}', returncode: {}".format(cmd, ret))
        raise subprocess.CalledProcessError(ret, 'openocd_start_debug')

def openocd_terminate():
    killall("openocd")

def killall(name):
    l = process_pid_list(name)
    for pid in l:
        os.kill(pid, signal.SIGTERM)

def write_stream_to_file(filename, request_iterator):
        file = open(filename, "wb")
        for request in request_iterator:
            file.write(request.data)
        file.close()

def process_pid_list(name):
    res = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if (proc.name() == name):
                res.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return res


class LogReader:
    def __init__(self):
      self.done = False
      pass

    def read(self, filename):
      with open(filename, 'r') as file:
          line = ''
          while not self.done:
              tmp = file.readline()
              if tmp != "":
                  line += tmp
                  if line.endswith("\n"):
                      yield line
                      line = ''
              else:
                  sleep(0.1)

    def abort(self):
        self.done = True