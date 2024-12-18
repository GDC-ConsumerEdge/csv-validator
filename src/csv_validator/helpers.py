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
import ipaddress
from collections.abc import Hashable
from typing import Callable, Optional, Set, Annotated

import pydantic


def unique() -> Callable:
    """Validator function to be used by Pydantic for ensuring a value is unique
    in a set.  Since this is a closure over `seen`, we're assuming that the
    incoming data checked for uniqueness is small enough to fit in memory.

    Returns:
        Validator function
    """
    seen = set()

    def nested[T](v: Hashable) -> T:  # type: ignore
        """ Performs the uniqueness check. Incoming value must be hashable
        as we're using a set to hold all our "seen" values.

        Args:
            v: value to check for uniqueness

        Returns:
            unchanged value of v

        Raises:
            ValueError if value has already been seen, meaning it is not unique
        """
        if v in seen:
            raise ValueError(f'Value "{v} is not unique')
        seen.add(v)
        return v

    return nested


def coerce_splt_commas_rtn_set_strs(s: str) -> Optional[Set[str]]:
    """Splits a string on commas, strips whitespace off split strings,
    returns as a set.  Only adds string to set if it is a non-empty string.

    Args:
        s: sting to split on commas

    Returns:
        Set of split, stripped strs or None

    """
    if s:
        return set(e.strip() for e in s.split(',') if e)
    return None


def coerce_empty_str_to_none(s: str) -> Optional[str]:
    """Takes a string and returns None if its empty, otherwise returns string
    Args:
        s: string

    Returns: String or None
    """
    if s:
        return s
    return None


def validate_cidr(ip: str) -> str:
    """Takes an IP and mask in CIDR notation, parses, validates, and returns
    with a normalized CIDR value
    Args:
        ip: string to parse as an IP CIDR pair

    Returns:
        String in coerced "ip/mask" format
    Raises:
        pydantic.ValidationError
    """
    return validate_ipv4_address(ip)


def validate_ipv4_address(ip: str, is_mandatory: bool = True) -> str:
    """ Validate an IPv4 address.

    Args:
        ip: IP with CIDR as string
        is_mandatory: If false, the value is optional

    Returns:

    """
    if not ip and not is_mandatory:
        return ip
    try:
        # Parse the CIDR notation using ip_network
        ipaddress.IPv4Network(ip, strict=False)
    except (ipaddress.AddressValueError, ValueError) as e:
        raise ValueError(f"Invalid CIDR value: {ip}. Error: {e}") from e

    return ip


EmailAddress = Annotated[str, pydantic.StringConstraints(
    pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', strip_whitespace=True)]

IP = Annotated[str, pydantic.AfterValidator(validate_ipv4_address)]
