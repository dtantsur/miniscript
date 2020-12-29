# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Reimplementations of common Ansible filters.

.. versionadded:: 1.1

.. note::
   Alternatively, can also use the `jinja2-ansible-filters project
   <https://pypi.org/project/jinja2-ansible-filters/>`_ but it will likely
   require licensing your code under GPL (the license Ansible uses).
"""

import itertools
import typing


_TRUE_VALUES = frozenset(['yes', 'true', '1'])


def bool_(value: typing.Any) -> bool:
    """Convert a value to a boolean according to Ansible rules.

    The corresponding filter is called ``bool`` (without an underscore).

    .. versionadded:: 1.1
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in _TRUE_VALUES
    elif isinstance(value, int):
        return value == 1
    else:
        return False


def dict2items(
    value: typing.Mapping,
    key_name: str = 'key',
    value_name: str = 'value',
) -> typing.List[typing.Dict[str, typing.Any]]:
    """Convert a mapping to a list of its items.

    For example, converts

    .. code-block:: yaml

        milk: 1
        eggs: 10
        bread: 2

    into

    .. code-block:: yaml

        - key: milk
          value: 1
        - key: eggs
          value: 10
        - key: bread
          value: 2

    .. versionadded:: 1.1

    :param value: Any mapping.
    :param key_name: Key name for input keys.
    :param value_name: Key name for input values.
    :returns: A list of dicts.
    """
    return [{key_name: key, value_name: value} for key, value in value.items()]


def items2dict(
    value: typing.List[typing.Mapping[str, typing.Any]],
    key_name: str = 'key',
    value_name: str = 'value',
) -> typing.Dict:
    """A reverse of :func:`dict2items`.

    For example, converts

    .. code-block:: yaml

        - key: milk
          value: 1
        - key: eggs
          value: 10
        - key: bread
          value: 2

    into

    .. code-block:: yaml

        milk: 1
        eggs: 10
        bread: 2

    .. versionadded:: 1.1

    :param value: A list of mappings.
    :param key_name: Key name for output keys.
    :param value_name: Key name for output values.
    :returns: A dictionary.
    """
    return {item[key_name]: item[value_name] for item in value}


def zip_(first: typing.Sequence, *other: typing.Sequence) -> typing.Iterator:
    """Zip two sequences together.

    The corresponding filter is called ``zip`` (without an underscore).

    .. versionadded:: 1.1
    """
    return zip(first, *other)


def zip_longest(
    first: typing.Sequence,
    *other: typing.Sequence,
    fillvalue: typing.Any = None,
) -> typing.Iterator:
    """Zip sequences together, always exhausing all of them.

    .. versionadded:: 1.1

    :param fillvalue: Value to fill shorter sequences with.
    """
    return itertools.zip_longest(first, *other, fillvalue=fillvalue)
