#!/usr/bin/python
#
# Copyright (C) 2021 Jacob Schultz Andersen schultz.jacob@gmail.com
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
from pathlib import Path

GDBINIT = """tui enable
layout split
focus cmd
set print pretty
set print asm-demangle on
set mem inaccessible-by-default off
set pagination off
compare-sections
b main
"""

OPENOCD_GDBINIT = """define restart
  mon reset halt
end

define rerun
  mon reset halt
  c
end
"""

OPENOCD = """source [find interface/cmsis-dap.cfg]

transport select swd
source [find target/stm32f4x.cfg]
reset_config none

proc itm_log { OUTPUT F_CPU {BAUDRATE 2000000} } {
	tpiu create itm.tpiu -dap [dap names] -ap-num 0 -protocol uart
	itm.tpiu configure -traceclk $F_CPU -pin-freq $BAUDRATE -output $OUTPUT
	itm.tpiu enable
	tpiu init
	itm port 0 on
}

proc program_device { SOURCE } {
	program $SOURCE verify
	reset run
	shutdown
}

init
"""

OCD_TOOL = """[DEFAULT]
config_path: @CONFIG@
# gdb defaults
config.1: gdbinit
config.2: openocd_gdbinit
gdb_executable: arm-none-eabi-gdb-py
gdb_args: -ex "target extended-remote :3333" -x @config.1@ -x @config.2@ @ELFFILE@
# openocd defaults
openocd_executable: openocd
config.ocd: openocd.cfg
openocd_args: -f @config.ocd@

# User defined key
gdb_pipe_gui: -iex 'target extended | openocd -c \\"gdb_port pipe\\" -f @config.ocd@'
gdb_pipe: -iex 'target extended | openocd -c "gdb_port pipe" -f @config.ocd@'

# User sections
[program]
openocd_args: -f @config.ocd@ -c "program_device {@ELFFILE@}"
mode: openocd

[log-itm]
openocd_args: -f @config.ocd@ -c "itm_log @TMPFILE@ @FCPU@"
mode: openocd

[gdb]
mode: gdb_openocd

[gui]
gdb_executable: gdbgui
gdb_args: '--gdb-cmd=${DEFAULT:gdb_executable} -ex "target extended-remote :3333" -x @config.1@ -x @config.2@ @ELFFILE@'
mode: gdb_openocd

# Gnome-terminal log
[gdb-log]
gdb_args: ${gdb_pipe} -x @config.1@ -x @config.2@ -ex "set logging file @TMPFILE@" -ex "set logging on" @ELFFILE@
spawn_process: gnome-terminal -- bash -c "tail -f @TMPFILE@"
mode: gdb

[gdb-pipe]
gdb_args: ${gdb_pipe} -x @config.1@ -x @config.2@ @ELFFILE@
mode: gdb

[gui-pipe]
gdb_executable: gdbgui
gdb_args: --gdb-cmd="${DEFAULT:gdb_executable} ${gdb_pipe_gui} -x @config.1@ -x @config.2@ @ELFFILE@"
mode: gdb
"""

def create_default_config(path):
    Path(path).mkdir()
    with Path(path, 'gdbinit').open(mode='w') as f: f.write(GDBINIT)
    with Path(path, 'openocd_gdbinit').open(mode='w') as f: f.write(OPENOCD_GDBINIT)
    with Path(path, 'openocd.cfg').open(mode='w') as f: f.write(OPENOCD)
    with Path(path, 'openocd-tool.cfg').open(mode='w') as f: f.write(OCD_TOOL)