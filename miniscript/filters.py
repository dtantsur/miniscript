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

from collections import abc as abcoll
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


def _combine_lists(
    first: typing.Sequence,
    second: typing.Sequence,
    list_merge: str,
) -> typing.Sequence:
    if list_merge == 'replace':
        return second
    elif list_merge == 'keep':
        return first
    elif list_merge == 'append':
        return list(itertools.chain(first, second))
    elif list_merge == 'prepend':
        return list(itertools.chain(second, first))
    else:
        first = [item for item in first if item not in set(second)]
        if list_merge == 'append_rp':
            return list(itertools.chain(first, second))
        else:
            return list(itertools.chain(second, first))


def _combine_dicts(
    first: typing.Mapping,
    second: typing.Mapping,
    recursive: bool = False,
    list_merge: str = 'replace',
) -> typing.Dict:
    result = dict(first)

    for key, value in second.items():
        try:
            existing = result[key]
        except KeyError:
            pass
        else:
            if (recursive and isinstance(existing, abcoll.MutableMapping)
                    and isinstance(value, abcoll.Mapping)):
                value = _combine_dicts(existing, value)
            elif (isinstance(existing, abcoll.Sequence)
                    and isinstance(value, abcoll.Sequence)):
                value = _combine_lists(existing, value, list_merge)

        result[key] = value

    return result


_VALID_LIST_MERGE = frozenset(['replace', 'keep', 'append', 'prepend',
                               'append_rp', 'prepend_rp'])


def combine(
    value: typing.Union[typing.Sequence[typing.Mapping], typing.Mapping],
    *other: typing.Mapping,
    recursive: bool = False,
    list_merge: str = 'replace',
) -> typing.Dict:
    """Combine several dictionaries into one.

    .. versionadded:: 1.1

    :param recursive: Whether to merge dictionaries recursively.
    :param list_merge: How to merge lists, one of ``replace``, ``keep``,
        ``append``, ``prepend``, ``append_rp``, ``prepend_rp``. The ``_rp``
        variants remove items that are present in both lists from the left-hand
        list.
    """
    if list_merge not in _VALID_LIST_MERGE:
        raise TypeError(f"'{list_merge}' is not a valid list_merge value, "
                        f"valid are {', '.join(_VALID_LIST_MERGE)}")

    if not isinstance(value, abcoll.Sequence):
        value = [value]

    try:
        first, *reminder = itertools.chain(value, other)
    except ValueError:
        return {}

    result = dict(first)
    for item in reminder:
        result = _combine_dicts(result, item, recursive=recursive,
                                list_merge=list_merge)

    return result


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
