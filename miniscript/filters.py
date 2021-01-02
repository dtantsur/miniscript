"""Reimplementations of common Ansible filters.

.. versionadded:: 1.1

.. note::
   Alternatively, can also use the `jinja2-ansible-filters project
   <https://pypi.org/project/jinja2-ansible-filters/>`_ but it will likely
   require licensing your code under GPL (the license Ansible uses).
"""

from collections import abc as abcoll
import datetime
import itertools
import re
import typing
from urllib import parse as urlparse

try:
    import jmespath  # type: ignore
except ImportError:  # pragma: no cover
    jmespath = None

from . import _utils


_TRUE_VALUES = frozenset(['yes', 'true', '1'])

__all__ = ['bool_', 'combine', 'dict2items', 'difference', 'flatten',
           'intersect', 'ipaddr', 'ipv4', 'ipv6', 'items2dict', 'json_query',
           'regex_escape', 'regex_findall', 'regex_replace', 'regex_search',
           'symmetric_difference', 'to_datetime', 'union', 'urlsplit', 'zip_',
           'zip_longest']


def bool_(value: typing.Any) -> bool:
    """Convert a value to a boolean according to Ansible rules.

    The corresponding filter is called ``bool`` (without an underscore).
    True values are ``True``, strings "Yes", "True" and "1", number 1;
    everything else is False.

    .. code-block:: yaml

        - vars:
            is_true: "{{ 'YES' | bool }}"

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

    A typical pattern of adding a value to a dictionary:

    .. code-block:: yaml

        - vars:
            new_dict: "{{ old_dict | combine({'new key': 'new value'}) }}"

    When a list is provided as input, all items from it are combined.

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


def difference(value: list, other: list) -> list:
    """Difference of two lists.

    .. code-block:: yaml

        - vars:
            new_list: "{{ [2, 4, 6, 8, 12] | difference([3, 6, 9, 12, 15]) }}"
            # -> [2, 4, 8]

    .. versionadded:: 1.1
    """
    return list(set(value).difference(other))


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
    value: list,
    levels: typing.Optional[int] = None
) -> list:
    """Flatten a list.

    .. code-block:: yaml

        - vars:
            new_list: "{{ [1, 2, [3, [4, 5, [6]], 7]] | flatten }}"
            # -> [1, 2, 3, 4, 5, 6, 7]

    To flatten only the top level, use the ``levels`` argument:

    .. code-block:: yaml

        - vars:
            new_list: "{{ [1, 2, [3, [4, 5, [6]], 7]] | flatten(levels=1) }}"
            # -> [1, 2, 3, [4, 5, [6]], 7]

    .. versionadded:: 1.1

    :param levels: Number of levels to flatten. If `None` - flatten everything.
    """
    return list(_utils.flatten(value, levels=levels))


def intersect(value: list, other: list) -> list:
    """Intersection of two lists.

    .. code-block:: yaml

        - vars:
            new_list: "{{ [2, 4, 6, 8, 12] | intersect([3, 6, 9, 12, 15]) }}"
            # -> [6, 12]

    .. versionadded:: 1.1
    """
    return list(set(value).intersection(other))


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

    .. versionadded:: 1.1
    """
    if jmespath is None:
        raise RuntimeError("The json_query filter requires jmespath "
                           "python package to be installed")
    return jmespath.search(query, value)


def regex_escape(value: str) -> str:
    """Escape special regular expression characters in a string.

    .. versionadded:: 1.1
    """
    return re.escape(value)


def regex_findall(
    value: str,
    pattern: str,
    *,
    multiline: bool = False,
    ignorecase: bool = False,
) -> typing.List[str]:
    """Find all occurencies of a pattern in a string.

    For example:

    .. code-block:: yaml

        - vars:
            url: "http://www.python.org"

        - return: "{{ url | regex_findall('(?<=\\\\W)\\\\w{3}(?=\\\\W|$)') }}"
          # returns ['www', 'org']

    .. versionadded:: 1.1

    :param pattern: Python regular expression.
    :param multiline: Whether ^ matches a beginning of each line, not just
        beginning of the string.
    :param ignorecase: Whether to ignore case when matching.
    """
    flags = _utils.regex_flags(multiline, ignorecase)
    return [x.group(0) for x in re.finditer(pattern, value, flags=flags)]


def regex_replace(
    value: str,
    pattern: str,
    replacement: str = '',
    *,
    multiline: bool = False,
    ignorecase: bool = False,
    count: int = 0,
) -> str:
    """Replace all occurencies of a pattern in a string.

    MiniScript implements Ansible-compatible slashes handling to avoid
    duplication of slashes inside Jinja expressions.

    .. code-block:: yaml

        - vars:
            url: "http://www.python.org"

        - return: "{{ url | regex_replace('(?<=\\\\W)\\\\w{3}(?=\\\\W|$)',
                                          '\\"\\\\1\\") }}"
          # returns 'http://"www".python."org"'

    .. versionadded:: 1.1

    :param pattern: Python regular expression.
    :param replacement: String to replace with, an empty string by default.
    :param multiline: Whether ^ matches a beginning of each line, not just
        beginning of the string.
    :param ignorecase: Whether to ignore case when matching.
    :param count: How many occurencies to replace. Zero (the default) means
        replace all.
    """
    flags = _utils.regex_flags(multiline, ignorecase)
    return re.sub(pattern, replacement, value, count=count, flags=flags)


def regex_search(
    value: str,
    pattern: str,
    *,
    multiline: bool = False,
    ignorecase: bool = False,
) -> str:
    """Find an occurence of a pattern in a string.

    .. versionadded:: 1.1

    :param pattern: Python regular expression.
    :param multiline: Whether ^ matches a beginning of each line, not just
        beginning of the string.
    :param ignorecase: Whether to ignore case when matching.
    """
    flags = _utils.regex_flags(multiline, ignorecase)
    match = re.search(pattern, value, flags=flags)
    return match.group(0) if match is not None else ""


def symmetric_difference(value: list, other: list) -> list:
    """Symmetric difference (exclusive OR) of two lists.

    .. code-block:: yaml

        - vars:
            new_list: "{{ [2, 4, 6, 8, 12]
                          | symmetric_difference([3, 6, 9, 12, 15]) }}"
            # -> [2, 3, 4, 8, 9, 15]

    .. versionadded:: 1.1
    """
    return list(set(value).symmetric_difference(other))


def to_datetime(
    value: str,
    format: str = "%Y-%m-%d %H:%M:%S",
) -> datetime.datetime:
    """Parse a date/time according to the format.

    The default format is ``%Y-%m-%d %H:%M:%S``.

    .. versionadded:: 1.1
    """
    return datetime.datetime.strptime(value, format)


def union(value: list, other: list) -> list:
    """Union of two lists.

    .. code-block:: yaml

        - vars:
            new_list: "{{ [2, 4, 6, 8, 12] | union([3, 6, 9, 12, 15]) }}"
            # -> [2, 3, 4, 6, 8, 9, 12, 15]

    .. versionadded:: 1.1
    """
    return list(set(value).union(other))


_URL_COMPONENTS = frozenset(['fragment', 'hostname', 'netloc', 'password',
                             'username', 'path', 'port', 'query', 'scheme'])


def urlsplit(
    value: str,
    query: typing.Optional[str] = None,
) -> typing.Union[typing.Dict, str]:
    """Split a URL into components.

    Known components are fragment, hostname, netloc, password, path, port,
    query, scheme, username.

    .. versionadded:: 1.1

    :param query: Requested component. If `None`, all components are returned
        in a dictionary.
    """
    parsed = urlparse.urlsplit(value)
    if query is not None:
        # Don't do getattr(parsed, query), risk exposing internal attributes!
        if query not in _URL_COMPONENTS:
            raise AttributeError(f"Unknown URL component '{query}'")

        return getattr(parsed, query)
    else:
        return {
            item: getattr(parsed, item)
            for item in _URL_COMPONENTS
        }


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
