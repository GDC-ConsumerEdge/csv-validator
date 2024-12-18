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

from csv_validator.helpers import coerce_empty_str_to_none
from csv_validator.model import StrippedStr, OptionalStrippedStr, BaseCluster

# SyncInterval type requires string to adhere to time regex; is optional, converts to None if field is empty in CSV
SyncInterval = typing.Annotated[
    typing.Optional[StrippedStr], pydantic.StringConstraints(pattern='^[0-9]*[hms]$'),
    pydantic.BeforeValidator(coerce_empty_str_to_none)]


class SourceOfTruthModel(BaseCluster):
    platform_repository: StrippedStr
    platform_repository_revision: StrippedStr
    platform_repository_sync_interval: SyncInterval = None
    platform_repository_branch: OptionalStrippedStr = None
    workload_repository: StrippedStr
    workload_repository_revision: StrippedStr
    workload_repository_sync_interval: SyncInterval = None
    workload_repository_branch: OptionalStrippedStr = None
