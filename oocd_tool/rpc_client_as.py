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
import contextlib
import oocd_tool.openocd_pb2 as openocd_pb2
import oocd_tool.openocd_pb2_grpc as openocd_pb2_grpc
import oocd_tool._credentials as _credentials
import asyncio

def _setup_cancel_request(generator):
    def cancel_request(unused_signum, unused_frame):
        generator.cancel()
        sys.exit(0)

    signal.signal(signal.SIGINT, cancel_request)

class AuthGateway(grpc.AuthMetadataPlugin):
    def __init__(self, auth_key):
        self.auth_key = auth_key

    def __call__(self, context, callback):
        signature = context.method_name[::-1]
        callback(((self.auth_key, signature),), None)

@contextlib.contextmanager
def insecure_channel(addr, unused_signatur):
    yield grpc.aio.insecure_channel(addr)

@contextlib.contextmanager
def secure_channel(addr, auth):
    call_credentials = grpc.aio.metadata_call_credentials(
        AuthGateway(auth), name='auth gateway')
    channel_credential = grpc.aio.ssl_channel_credentials(
        _credentials.ROOT_CERTIFICATE)
    composite_credentials = grpc.aio.composite_channel_credentials(
        channel_credential, call_credentials)

    channel = grpc.aio.secure_channel(addr, composite_credentials)
    yield channel

def load_certificates(config):
    _credentials.load_certificates(config)

class ClientChannel:
    def __init__(self, host, channel, auth):
        self._host = host
        self._channel_type = channel
        self._auth_key = auth

    def is_secure(self):
        return self._channel_type == secure_channel

    async def log_stream_create(self, file, proc):
        async with self._channel_type(self._host, self._auth_key) as channel:
            stub = openocd_pb2_grpc.aio.OpenOcdStub(channel)

            result_generator = await stub.LogStreamCreate(openocd_pb2.LogStreamRequest(filename=file))
            _setup_cancel_request(result_generator)

            async for result in result_generator:
                proc(result.data.strip())

    def program_device(self, file):
        with self._channel_type(self._host, self._auth_key) as channel:
            stub = openocd_pb2_grpc.aio.OpenOcdStub(channel)

            def file_reader(filename):
                with open(filename, 'rb') as file:
                    while chunk := file.read(2048):
                        request = openocd_pb2.ProgramRequest(data=chunk)
                        yield request

            result_generator = stub.ProgramDevice(file_reader(file))
            _setup_cancel_request(result_generator)

            for result in result_generator:
               yield result.data.strip()

    def reset_device(self):
        with self._channel_type(self._host, self._auth_key) as channel:
            stub = openocd_pb2_grpc.aio.OpenOcdStub(channel)
            result_generator = stub.ResetDevice(openocd_pb2.void())
            _setup_cancel_request(result_generator)

            for result in result_generator:
               yield result.data.strip()


    @contextlib.contextmanager
    def debug_device(self):
        with self._channel_type(self._host, self._auth_key) as channel:
            stub = openocd_pb2_grpc.aio.OpenOcdStub(channel)
        try:
            stub.StartDebug(openocd_pb2.void())
            yield
        finally:
            stub.StopDebug(openocd_pb2.void())



def get_credentials(shared_secret):
    call_credentials = grpc.metadata_call_credentials(AuthGateway(shared_secret), name='auth gateway')
    channel_credential = grpc.ssl_channel_credentials(_credentials.ROOT_CERTIFICATE)
    return grpc.composite_channel_credentials(channel_credential, call_credentials)


async def test(file, proc):
    async with grpc.aio.secure_channel("pi:50051", get_credentials("my-secret-key_blabla")) as channel:
        stub = openocd_pb2_grpc.OpenOcdStub(channel)

        result_generator = stub.LogStreamCreate(openocd_pb2.LogStreamRequest(filename=file))
        _setup_cancel_request(result_generator)

        async for result in result_generator:
            proc(result.data.strip())


class LogStream:
    def __init__(self, file):
        self.channel = grpc.aio.secure_channel("pi:50051", get_credentials("my-secret-key_blabla"))
        stub = openocd_pb2_grpc.OpenOcdStub(self.channel)
        self.result_generator = stub.LogStreamCreate(openocd_pb2.LogStreamRequest(filename=file))

    async def _output_stream(self, callback):
        async for result in self.result_generator:
            callback(result.data)
        self.channel.close()

    def cancel(self):
        self.result_generator.cancel()

    def start_output(self, callback):
        asyncio.create_task(self._output_stream(callback))