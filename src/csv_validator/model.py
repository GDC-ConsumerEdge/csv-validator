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
from typing import Annotated, Optional

import pydantic

from csv_validator.helpers import coerce_splt_commas_rtn_set_strs, \
    coerce_empty_str_to_none, unique

# StrippedStr is a strict string type that trims/strips off whitespace on
# both ends
StrippedStr = Annotated[
    str, pydantic.StringConstraints(strict=True, strip_whitespace=True)]

# An *optional* `StrippedStr` typ, allows None; converts an empty string (an
# empty field from a CSV) to None
OptionalStrippedStr = Annotated[
    Optional[StrippedStr],
    pydantic.BeforeValidator(coerce_empty_str_to_none)]

# ClusterName is strict, strips whitespace, lower-cased, and unique. This may
# optionally adhere to a strict regex pattern by supplying the `pattern`
# keyword to `pydantic.StringConstraints`.  More here:
# https://docs.pydantic.dev/latest/api/types/#pydantic.types.StringConstraints
ClusterName = Annotated[
    str,
    pydantic.StringConstraints(strict=True, strip_whitespace=True,
                               to_lower=True, min_length=1, max_length=30),
    pydantic.AfterValidator(unique())]

# ClusterTags type is an optional set of valid tags
# Currently set to any valid str; should be an enum
ClusterTags = Annotated[
    Optional[set[str]],
    pydantic.BeforeValidator(coerce_empty_str_to_none),
    pydantic.BeforeValidator(coerce_splt_commas_rtn_set_strs)]


class BaseCluster(pydantic.BaseModel, extra='forbid'):
    """
    Contains reference model for basic cluster-related values.  This model is
    meant to be subclassed and extended for table-specific values.
    """
    cluster_name: ClusterName
    cluster_group: str
    cluster_tags: ClusterTags

    @pydantic.field_serializer('cluster_tags')
    def dump_set_of_vals(self, vals: set[str]) -> str:
        """ Takes a set of values and returns them as a comma-joined string
        if vals is not None. The value prop of making this a
        `pydantic.field_serializer` is that these values are splat out by the
        "output" functionality of the CLI tool that dynamically imports this
        file.  We want to serialize the output to a string that is useful in
        CSV format.  This ensures the data that comes in meets expectations
        and that the output is nicely formed. """
        if vals:
            return ",".join(str(v) for v in vals)
        return ""
