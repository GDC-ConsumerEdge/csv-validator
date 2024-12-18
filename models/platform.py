###############################################################################
# Copyright 2024 Google, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
import typing

import pydantic

from csv_validator.helpers import coerce_empty_str_to_none, coerce_splt_commas_rtn_set_strs, IP
from csv_validator.model import StrippedStr, BaseCluster

# SyncInterval type requires string to adhere to time regex; is optional, converts to None if field is empty in CSV
SyncInterval = typing.Annotated[
    typing.Optional[StrippedStr],
    pydantic.StringConstraints(pattern='^[0-9]*[hms]$'),
    pydantic.BeforeValidator(coerce_empty_str_to_none)
]

DNSServers = typing.Annotated[
    typing.Optional[set[IP]],
    pydantic.BeforeValidator(coerce_empty_str_to_none),  # Optional could be none; treat empty strings as None
    pydantic.BeforeValidator(coerce_splt_commas_rtn_set_strs),  # input is comma separated list; split on the commas
]


class SourceOfTruthModel(BaseCluster):
    dns_servers: DNSServers

    @pydantic.field_serializer('dns_servers')
    def dump_dns(self, dns_servers: set[IP]) -> str:
        if dns_servers:
            return ",".join(str(ip) for ip in dns_servers)
