#
# Copyright (C) 2021 Jacob Schultz Andersen schultz.jacob@gmail.com
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import sys
import grpc
import signal
import oocd_tool.openocd_pb2 as openocd_pb2
import oocd_tool.openocd_pb2_grpc as openocd_pb2_grpc

def _setup_cancel_request(generator):
    def cancel_request(unused_signum, unused_frame):
        generator.cancel()
        sys.exit(0)

    signal.signal(signal.SIGINT, cancel_request)


def log_stream_create(host, file):
    with grpc.insecure_channel(host) as channel:

        stub = openocd_pb2_grpc.OpenOcdStub(channel)
        result_generator = stub.LogStreamCreate(openocd_pb2.LogStreamRequest(filename=file))
        _setup_cancel_request(result_generator)

        for result in result_generator:
            print(result.data.strip())


def program_device(host, file):
    with grpc.insecure_channel(host) as channel:
        stub = openocd_pb2_grpc.OpenOcdStub(channel)

        def file_reader(filename):
            with open(filename, 'rb') as file:
                while chunk := file.read(2048):
                    request = openocd_pb2.ProgramRequest(data=chunk)
                    yield request

        result_generator = stub.ProgramDevice(file_reader(file))
        _setup_cancel_request(result_generator)

        for result in result_generator:
            print(result.data.strip())

def reset_device(hostname):
    with grpc.insecure_channel(hostname) as channel:
        stub = openocd_pb2_grpc.OpenOcdStub(channel)
        stub.ResetDevice(openocd_pb2.void())


class RemoteDebug:
    def __init__(self, host):
        self.host = host
    def __enter__(self):
        with grpc.insecure_channel(self.host) as channel:
            stub = openocd_pb2_grpc.OpenOcdStub(channel)
            stub.StartDebug(openocd_pb2.void())
    def __exit__(self, type, value, traceback):
        with grpc.insecure_channel(self.host) as channel:
            stub = openocd_pb2_grpc.OpenOcdStub(channel)
            stub.StopDebug(openocd_pb2.void())
