# openocd-tool
A flexible configuration tool for debugging and programming embedded devices with openocd.

### Usage
Define custom sections as needed using python syntax for [configparser.ExtendedInterpolation](https://docs.python.org/3/library/configparser.html)
A default .openocd-tool directory with example files is create in the home dir (at first run). Can be overwritten on command line with a '-c'.

config.xx: keys can be defined as desired. They can be specified with full path or none, they are prefix with the default configuration folder if no path is given.

`openocd-tool [-c openocd-tool.cfg]  <action>   /some_path/elffile`

Use '-d' for a dry run. Prints only final commands.

**Tags avalible:**
```
@TMPFILE@  creates a temporary file
@CONFIG@   equales to default config path or path from '-c' on command line
@FCPU@     value from '--fcpu' parameter
@ELFFILE@  elf filename
```
**Modes:**
```
gdb          Runs gdb standalone
openocd      Runs openocd standalone
gdb_openocd  Script spawns openocd in backgroup
```

**Configuration example:**
```ini
[DEFAULT]
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
gdb_pipe: -iex 'target extended | openocd -c \"gdb_port pipe\" -f @config.ocd@'

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

[gdb-pipe]
gdb_args: ${gdb_pipe} -x @config.1@ -x @config.2@ @ELFFILE@
mode: gdb

[gui-pipe]
gdb_executable: gdbgui
gdb_args: --gdb-cmd="${DEFAULT:gdb_executable} ${gdb_pipe} -x @config.1@ -x @config.2@ @ELFFILE@"
mode: gdb
```

**Installation:**

```sh
git clone git@github.com:jasa/openocd-tool.git
cd openocd-tool
python -m build
pip install dist/openocd-tool-0.0.1.tar.gz --user
```

**Issues**
* log-itm support is not finished yet.

