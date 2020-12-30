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

try:
    import jmespath  # type: ignore
except ImportError:  # pragma: no cover
    jmespath = None

from . import _utils


_TRUE_VALUES = frozenset(['yes', 'true', '1'])

__all__ = ['bool_', 'combine', 'dict2items', 'flatten',
           'ipaddr', 'ipv4', 'ipv6', 'items2dict',
           'json_query', 'zip_', 'zip_longest']


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
    if list_merge not in _utils.VALID_LIST_MERGE:
        raise TypeError(f"'{list_merge}' is not a valid list_merge value, "
                        f"valid are {', '.join(_utils.VALID_LIST_MERGE)}")

    if not isinstance(value, abcoll.Sequence):
        value = [value]

    try:
        first, *reminder = itertools.chain(value, other)
    except ValueError:
        return {}

    result = dict(first)
    for item in reminder:
        result = _utils.combine_dicts(result, item, recursive=recursive,
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


def flatten(
    value: typing.List,
    levels: typing.Optional[int] = None
) -> typing.List:
    """Flatten a list.

    .. versionadded:: 1.1

    :param levels: Number of levels to flatten. If `None` - flatten everything.
    """
    return list(_utils.flatten(value, levels=levels))


def ipaddr(
    value: typing.Union[str, int],
    query: typing.Optional[str] = None,
) -> str:
    """Filter IP addresses and networks.

    .. versionadded:: 1.1

    Implements Ansible `ipaddr filter
    <https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters_ipaddr.html>`_.
    """
    return _utils.ip_filter(value, query=query)


def ipv4(
    value: typing.Union[str, int],
    query: typing.Optional[str] = None,
) -> str:
    """Filter IPv4 addresses and networks.

    .. versionadded:: 1.1

    Implements Ansible `ipv4 filter
    <https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters_ipaddr.html>`_.
    """
    return _utils.ip_filter(value, version=4, query=query)


def ipv6(
    value: typing.Union[str, int],
    query: typing.Optional[str] = None,
) -> str:
    """Filter IPv6 addresses and networks.

    .. versionadded:: 1.1

    Implements Ansible `ipv6 filter
    <https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters_ipaddr.html>`_.
    """
    return _utils.ip_filter(value, version=6, query=query)


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


def json_query(value: typing.Any, query: str) -> typing.Any:
    """Run a JSON query against the data.

    Requires the `jmespath <https://pypi.org/project/jmespath/>`_ library.
    See `jmespath examples <https://jmespath.org/examples.html>`_.
    """
    if jmespath is None:
        raise RuntimeError("The json_query filter requires jmespath "
                           "python package to be installed")
    return jmespath.search(query, value)


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
