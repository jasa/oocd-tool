#
# Copyright (C) 2021 Jacob Schultz Andersen schultz.jacob@gmail.com
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
from pathlib import Path

_GDBINIT = """tui enable
layout split
focus cmd
set print pretty
set print asm-demangle on
set mem inaccessible-by-default off
set pagination off
compare-sections
b main
"""

_OPENOCD_GDBINIT = """define restart
  mon reset halt
end

define rerun
  mon reset halt
  c
end
"""

_OPENOCD = """bindto 0.0.0.0
source [find interface/cmsis-dap.cfg]

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

proc reset_device { } {
	reset run
	shutdown
}

init
"""

_OCD_TOOL = """[DEFAULT]
config_path: @CONFIG@
# gdb defaults
config.1: gdbinit
config.2: openocd_gdbinit
gdb_executable: arm-none-eabi-gdb-py
gdb_args: -ex "target extended-remote pi:3333" -x @config.1@ -x @config.2@ @ELFFILE@
openocd_remote: pi:50051

# User sections
[program]
openocd_args: program @ELFFILE@
mode: openocd

[reset]
openocd_args: reset
mode: openocd

[log]
openocd_args: logstream /tmp/test.log
mode: openocd

[gdb]
mode: gdb

[gui]
gdb_executable: gdbgui
gdb_args: '--gdb-cmd=${DEFAULT:gdb_executable} ${DEFAULT:gdb_args}'
mode: gdb
"""

_OCD_RPCD = """[DEFAULT]
bindto: 0.0.0.0:50051
cmd_program: openocd -f /home/ocd/.oocd-tool/openocd.cfg -c "program_device /tmp/program.elf"
cmd_reset: openocd -f /home/ocd/.oocd-tool/openocd.cfg -c "reset_device"
cmd_debug: /usr/bin/openocd -f /home/ocd/.oocd-tool/openocd.cfg
[log]
file: /tmp/ocd-rpcd.log
level: ERROR
"""

_OCD_RPCD_SERVICE = """[Unit]
Description=OpenOCD gRPC Service
After=network.target

[Service]
# Bug in gRPC version 1.42 environment variable can be delete in future versions.
Environment="LD_PRELOAD=/usr/lib/gcc/arm-linux-gnueabihf/10/libatomic.so"
ExecStart=/home/ocd/.local/bin/oocd-rpcd /home/ocd/.oocd-tool/oocd-rpcd.cfg
User=ocd
KillMode=process
Restart=always
RestartSec=10
Type=simple

[Install]
WantedBy=multi-user.target
"""

def create_default_config(path):
    Path(path).mkdir()
    with Path(path, 'gdbinit').open(mode='w') as f: f.write(_GDBINIT)
    with Path(path, 'openocd_gdbinit').open(mode='w') as f: f.write(_OPENOCD_GDBINIT)
    with Path(path, 'openocd.cfg').open(mode='w') as f: f.write(_OPENOCD)
    with Path(path, 'oocd-tool.cfg').open(mode='w') as f: f.write(_OCD_TOOL)
    with Path(path, 'oocd-rpcd.cfg').open(mode='w') as f: f.write(_OCD_RPCD)
    with Path(path, 'oocd-rpcd.service').open(mode='w') as f: f.write(_OCD_RPCD_SERVICE)
