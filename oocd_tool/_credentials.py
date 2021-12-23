# Copyright 2019 The gRPC Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os


def _load_credential_from_file(filepath):
    real_path = os.path.join(os.path.dirname(__file__), filepath)
    with open(real_path, 'rb') as f:
        return f.read()


SERVER_CERTIFICATE = _load_credential_from_file('credentials/localhost.crt')
SERVER_CERTIFICATE_KEY = _load_credential_from_file('credentials/localhost.key')
ROOT_CERTIFICATE = _load_credential_from_file('credentials/root.crt')


def load_certificates(config):
    if 'root_ca' in config:
        global ROOT_CERTIFICATE
        ROOT_CERTIFICATE = _load_credential_from_file(config.root_ca)
    if 'server_cert' in config:
        global SERVER_CERTIFICATE
        SERVER_CERTIFICATE = _load_credential_from_file(config.server_cert)
    if 'server_key' in config:
        global SERVER_CERTIFICATE_KEY
        SERVER_CERTIFICATE_KEY = _load_credential_from_file(config.server_key)


