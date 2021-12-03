# oocd-tool
### A flexible configuration and remote contol tool for openocd. 

This tool was made to create a wireless development environment for a project. It's made public since a lack of easy solutions and it will be developed futher if there an interrest for this tool.

**Features**
1. Controls openocd remotely through gRPC. Makes wireless debugging/programming possible with a raspberry pi.
2. Runs openocd as background process then debugging. (Windows compatible)
3. Runs gdb/openocd in pipe mode.
4. Capable of log streaming from remote openocd host.

### Usage
Define custom sections as needed using python syntax for [configparser.ExtendedInterpolation](https://docs.python.org/3/library/configparser.html)
A default .oocd-tool directory with example files is create in the home dir (at first run). Can be overwritten on command line with a '-c'.

config.xx: keys defines config files. They can be specified with full path or none, they are prefix with the default configuration directory if no path is given.

3 configuration files is available in the examples directory for each operation mode. (remote.cfg, pipe.cfg and spawn.cfg).
The active default configuration is should be placed in ~/.oocd-tool/oocd-tool.cfg with the rest of the configuration files.

Command line syntax:

`oocd-tool [-c oocd-tool.cfg]  <action>   /some_path/elffile`

Use '-d' for a dry run. Prints only commands.

Command line syntax gRPC daemon, see examples folder for configuration:
`oocd-rpcd -c oocd-rpcd.cfg`

**Tags avalible:**
```
@TMPFILE@  creates a temporary file. May only be used in pairs once, and not in default section.
@CONFIG@   equales to default config path or path from '-c' on command line
@FCPU@     value from '--fcpu' parameter
@ELFFILE@  elf filename
```

**Modes:**
```
gdb          Runs gdb standalone / openocd remotely.
openocd      Runs openocd standalone, localy or remotely.
gdb_openocd  Spawns openocd in backgroup (used for Windows support).
```

**Installation:**

```sh
git clone git@github.com:jasa/oocd-tool.git
cd oocd-tool
python -m build
pip install dist/oocd-tool-0.0.3.tar.gz --user
```

### Installation of RPC daemon on a remote pi4.
```bash
# Tested on: Pi OS - Debian Buster
sudo apt install openocd

sudo adduser ocd
su - ocd
git clone https://github.com/jasa/oocd-tool.git
cd oocd-tool
python -m build
pip install dist/oocd_tool-0.0.3.tar.gz
cp examples/oocd-rpcd.service to /etc/systemd/system
mkdir ~/.oocd-tool
cp examples/openocd.cfg ~/.oocd-tool
# install your programming device (st-link, cmsis-dap, ...) and copy needed file to `/etc/udev.rules.d`
# edit config file ~/.oocd-tool/openocd.cfg as needed
# exit as 'ocd' user
sudo usermod -g <udev group>   # if needed
sudo udevadm control --reload-rules
sudo udevadm trigger

sudo systemctl daemon-reload
sudo systemctl start oocd-rpcd
sudo systemctl enable oocd-rpcd
```

**Status**
* Tested superficial in Windows with openocd 0.11.0, gdb 10.3
* A ELF is mandatory on command line, even if it's not used. Needs to be fixed.

