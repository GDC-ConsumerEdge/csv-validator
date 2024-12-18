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
import enum
import typing

import pydantic

from csv_validator.helpers import (coerce_empty_str_to_none, coerce_splt_commas_rtn_set_strs,
                                   validate_ipv4_address, EmailAddress)
from csv_validator.model import BaseCluster

# IP uses StingConstraints to strip and filter incoming data: https://docs.pydantic.dev/latest/api/types/#pydantic.types.StringConstraints
IP = typing.Annotated[str, pydantic.AfterValidator(validate_ipv4_address)]

# an optional (could be `None`) set of strings
# uses BeforeValidator on the incoming data: https://docs.pydantic.dev/latest/api/functional_validators/#pydantic.functional_validators.BeforeValidator
optional_unique_values = typing.Annotated[
    typing.Optional[set[str]],
    pydantic.BeforeValidator(coerce_empty_str_to_none),  # Optional could be none; treat empty strings as None
    pydantic.BeforeValidator(coerce_splt_commas_rtn_set_strs),  # input is comma separated list as str
]


class HamSandwichIngredients(enum.StrEnum):
    BREAD = 'bread'
    HAM = 'ham'
    MUSTARD = 'mustard'
    MAYO = 'mayo'
    LETTUCE = 'lettuce'
    PICKLES = 'pickles'


class ApprovedRepos(enum.StrEnum):
    """ Defines an enumeration of "approved repos" """
    us_edge_workloads = 'https://github.com/edge-config-sync-org/us-edge-workloads.git'
    us_edge_platform = 'https://github.com/edge-config-sync-org/us-edge-platform.git'
    au_edge_workloads = 'https://github.com/edge-config-sync-org/au-edge-workloads.git'
    au_edge_platform = 'https://github.com/edge-config-sync-org/au-edge-platform.git'

# expects a set of `HamSandwichIngredients`
# uses BeforeValidator on the incoming data: https://docs.pydantic.dev/latest/api/functional_validators/#pydantic.functional_validators.BeforeValidator
UniqueSetOfValuesType = typing.Annotated[
    set[HamSandwichIngredients],
    pydantic.BeforeValidator(coerce_empty_str_to_none),
    pydantic.BeforeValidator(coerce_splt_commas_rtn_set_strs)
]

# expects a set of `HamSandwichIngredients`, but it's optional (could be `None`)
# uses BeforeValidator on the incoming data: https://docs.pydantic.dev/latest/api/functional_validators/#pydantic.functional_validators.BeforeValidator
OptionalUniqueSetOfValuesType = typing.Annotated[
    typing.Optional[set[HamSandwichIngredients]],
    pydantic.BeforeValidator(coerce_empty_str_to_none),
    pydantic.BeforeValidator(coerce_splt_commas_rtn_set_strs)
]

# uses StingConstraints to strip and filter incoming data: https://docs.pydantic.dev/latest/api/types/#pydantic.types.StringConstraints
ValidEmailType = typing.Annotated[
    str, pydantic.StringConstraints(pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b',
                                    strip_whitespace=True)
]


class Group(enum.StrEnum):
    """ Used in `NewBase` below.  Each value is a valid group """
    US_LAB = 'us-lab'
    US = 'us'
    CANADA = 'ca'
    MEXICO = 'mx'


class Tag(enum.StrEnum):
    """ Used in `NewBase` below.  Each value is a valid tag """
    PROD = 'prod'
    NONPROD = 'nonprod'
    LAB = 'lab'
    DONOTUPGRADE = 'donotupgrade'
    CORPORATE = 'corp'
    FRANCHISE = 'franchise'


# Demonstrates how to use `Annotated` to tell Pydantic a few key things:
# * Uses `BeforeValidator` with a custom function to split the incoming string value on commas, returning it as a set
# * Takes that set and ensures that each split string is a value in the enum `Tag`
# * Creates a `set` of unique `Tag`s.
# uses BeforeValidator on the incoming data: https://docs.pydantic.dev/latest/api/functional_validators/#pydantic.functional_validators.BeforeValidator
ValidTag = typing.Annotated[set[Tag], pydantic.BeforeValidator(coerce_splt_commas_rtn_set_strs)]


class NewBase(BaseCluster):
    """ Overrides the base cluster and uses a custom set of groups and tags
    Note ValidTag is a custom type defined here, but why?  Because it will probably be a comma-separated set of tags as
    a string, and needs be split.
    """
    cluster_group: Group
    cluster_tags: ValidTag


class SourceOfTruthModel(NewBase):
    optional_value: typing.Annotated[typing.Optional[str], pydantic.BeforeValidator(coerce_empty_str_to_none)]
    unique_set_of_values: UniqueSetOfValuesType
    optional_unique_set_of_values: OptionalUniqueSetOfValuesType
    ip: IP
    network: IP
    repository: ApprovedRepos
    sha: typing.Annotated[str, pydantic.StringConstraints(pattern='^[abcdef0-9]{7}$', strip_whitespace=True)]
    tag: typing.Annotated[str, pydantic.StringConstraints(pattern=r'^v\d\.\d(.\d)?', strip_whitespace=True)]
    email: EmailAddress

    @pydantic.field_serializer('unique_set_of_values', 'optional_unique_set_of_values')
    def dump_set_of_vals(self, vals: set[str]) -> str:
        """ Takes a set of values and returns them as a comma-joined string if vals is not None.
        The value prop of making this a `pydantic.field_serializer` is that these values are splat out by the
        "output" functionality of the CLI tool that dynamically imports this file.  We want to serialize the
        output to a string that is useful in CSV format.  This ensures the data that comes in meets expectations
        and that the output is nicely formed.
        """
        if vals:
            return ",".join(str(v) for v in vals)
