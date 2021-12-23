[![Upload Python Package](https://github.com/jasa/oocd-tool/actions/workflows/python-publish.yml/badge.svg)](https://github.com/jasa/oocd-tool/actions/workflows/python-publish.yml)
# oocd-tool
### A flexible configuration and remote control tool for openocd.

This tool was made to create a wireless development environment for a project. It can hopefully be useful to someone else and any suggestions or ideas there can improve the tool are welcome.

**Features**
1. Controls openocd remotely through gRPC. Makes wireless debugging/programming possible with a raspberry pi.
2. Runs openocd as background process then debugging. (Windows compatible)
3. Runs gdb/openocd in pipe mode.
4. Capable of log streaming from remote openocd host.
5. TLS/SSL based transport layer with pre shared key.

### Usage
Define custom sections as needed using python syntax for [configparser.ExtendedInterpolation](https://docs.python.org/3/library/configparser.html)
A default .oocd-tool directory with example files is created in the home dir (at first run). Can be overwritten on command line with a '-c'.

config.xx: keys defines config files. They can be specified with full path or none, they are prefixed with the default configuration directory if no path is given.

3 configuration files is available in the examples' directory for each operation mode. (remote.cfg, pipe.cfg and spawn.cfg).
The active default configuration should be placed in ~/.oocd-tool/oocd-tool.cfg with the rest of the configuration files.

Command line syntax:

`oocd-tool [-c oocd-tool.cfg]  <action>   /some_path/elffile`

Use '-d' for a dry run. Prints only commands.

Command line syntax gRPC daemon, see examples folder for configuration:
`oocd-rpcd -c oocd-rpcd.cfg`

A usefully environment variable for debugging.
`export GRPC_VERBOSITY=debug`

**Tags available:**
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

**Security:**

For use in a unsecure environments overwrite the buildin certificates with you own. The RPC host itself is reasonably protected since there are no direct shell access for now. TLS mode is default on and should be explicitly disabled in the configuration.

**Installation:**

```sh
git clone git@github.com:jasa/oocd-tool.git
cd oocd-tool
python -m build
pip install dist/oocd-tool-0.0.3.tar.gz --user
```

**Installation of RPC daemon on a remote pi4.**
```bash
# Tested on: Pi OS - Debian Buster
sudo apt install openocd

sudo adduser ocd
su - ocd
git clone https://github.com/jasa/oocd-tool.git
cd oocd-tool
python -m build
pip install dist/oocd_tool-0.1.0.tar.gz
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

**Generate new certificate**
```
# On remote server

su - ocd
cd ~/.oocd-tool
~/oocd-tool/examples/gen-certificates.sh -cn <hostname>

vi oocd-rpc.cfg
# update following keys to:
#   server_key: /home/ocd/.oocd_tool/server_key.pem
#   server_cert: /home/ocd/.oocd_tool/server_cert.pem

# On Clients

# copy root_ca.pem to /you_home/.oocd-tool on all clients
# update following key in /you_home/.oocd-tool/oocd-tool.cfg on clients
#   root_ca: /your_home/.oocd_tool/ca_cert.pem

# REMEMBER to change shared secret `cert_auth_key` on both client and server.

```
**Status**
* Tested superficial in Windows with openocd 0.11.0, gdb 10.3
* `spawn_process` is not implemented as remote command yet.
* In gRPC version 1.42.0 on Pi OS is the following environment variable required 'LD_PRELOAD=/usr/lib/gcc/arm-linux-gnueabihf/10/libatomic.so'. due to linker problem, probably fixed in the gRPC release.
