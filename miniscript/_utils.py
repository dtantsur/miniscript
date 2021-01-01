from collections import abc as abcoll
import ipaddress
import itertools
import re
import typing


VALID_LIST_MERGE = frozenset(['replace', 'keep', 'append', 'prepend',
                              'append_rp', 'prepend_rp'])


def combine_lists(
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


def combine_dicts(
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
                value = combine_dicts(existing, value)
            elif (isinstance(existing, abcoll.Sequence)
                    and isinstance(value, abcoll.Sequence)):
                value = combine_lists(existing, value, list_merge)

        result[key] = value

    return result


def _ip_from_int(value):
    try:
        value = int(value)
    except ValueError:
        pass
    else:
        return value

    try:
        host, netmask = map(int, value.split('/', 1))
        ip = ipaddress.ip_address(host)
    except ValueError:
        return value

    return f"{ip}/{netmask}"


def _ip_match(value, query=None, version=None):
    # Prevent bool from being treated as 1/0
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return False

    value = _ip_from_int(value)

    try:
        ipaddr = ipaddress.ip_interface(value)
    except ValueError:
        return False

    if version is not None and version != ipaddr.version:
        return False

    try:
        ipnet = ipaddress.ip_network(value)
    except ValueError:
        is_net = False
    else:
        is_net = ipnet.num_addresses > 1

    # Canonical values for integers
    if isinstance(value, int):
        value = str(ipaddr.network if is_net else ipaddr.ip)

    if query is None:
        return value
    elif query == 'address':
        return str(ipaddr.ip) if not is_net else False
    elif query == 'host':
        return str(ipaddr) if not is_net else False
    elif query == 'public':
        return value if ipaddr.ip.is_global else False
    elif query == 'private':
        is_private = ipaddr.ip.is_private and not ipaddr.ip.is_loopback
        return value if is_private else False
    elif query == 'net':
        return value if is_net else False
    elif query == 'size':
        return ipaddr.network.num_addresses
    elif '/' in query:
        iprange = ipaddress.ip_network(query)
        return value if ipaddr.ip in iprange else False

    try:
        index = int(query)
    except ValueError:
        raise TypeError(f"Unknown query: {query}")
    else:
        return f"{ipaddr.network[index]}/{ipaddr.network.prefixlen}"


def ip_filter(value, query=None, version=None):
    if isinstance(value, (str, int)):
        return _ip_match(value, query=query, version=version)
    elif isinstance(value, abcoll.Sequence):
        result = (_ip_match(y, query=query, version=version) for y in value)
        return list(filter(None, result))
    else:
        return False


def flatten(
    value: typing.Iterable,
    levels: typing.Optional[int] = None
) -> typing.Iterable:
    if levels == 0:
        return value

    iterables = (
        flatten(x, levels=(None if levels is None else levels - 1))
        if isinstance(x, list) else (x,)
        for x in value
    )
    return itertools.chain.from_iterable(iterables)


def regex_flags(multiline: bool, ignorecase: bool) -> int:
    flags = 0
    if multiline:
        flags |= re.MULTILINE
    if ignorecase:
        flags |= re.IGNORECASE
    return flags
