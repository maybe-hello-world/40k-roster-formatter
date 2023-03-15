import logging
from typing import Optional, List, Callable

from lxml.objectify import ObjectifiedElement

MAX_SECONDARY_POINTS = 15


class FormatterException(Exception):
    pass


def single_children_by_name(children: List[ObjectifiedElement], name: str) -> Optional[ObjectifiedElement]:
    children = [x for x in children if x.get("name", None) == name]
    if len(children) == 1:
        return children[0]
    else:
        return None


def remove_prefix(_string: str, _prefix: str) -> str:
    if _string.startswith(_prefix):
        return _string[len(_prefix):]
    return _string


def remove_suffix(_string: str, _suffix: str) -> str:
    if _suffix and _string.endswith(_suffix):
        return _string[:-len(_suffix)]
    return _string


def expand_cps(cps: List[int]) -> str:
    if not cps:
        return '0'
    return ''.join([str(cps[0])] + [str(x) if x < 0 else f"+{x}" for x in cps[1:]])


def is_upgrade(_object: ObjectifiedElement) -> bool:
    """
    Because 'type'=='upgrade' not always mean that it's upgrade
    https://github.com/bsdata/wh40k/issues/11182

    New round of problems: some models in units are marked as 'upgrade' and do not have profiles.
    Let's keep the list of such units here as there no other way to fix this (except fixing BS data, of course)
    """
    damn_dirty_hacks = [
        "Biker Sergeant",
        "Space Marine Biker",
    ]

    if _object.get('type', None) == 'model':
        return False
    if _object.get('type', None) == 'unit':
        return False

    if hasattr(_object, 'profiles'):
        for profile in _object.profiles.getchildren():
            if profile.get('typeName', None) == 'Unit':
                logging.info(f"{_object.get('name', 'Unknown object')} is model/unit despite being marked as upgrade")
                return False

    for hack in damn_dirty_hacks:
        if _object.get('name', '').startswith(hack):
            return False

    return True


def try_parse_int(_obj) -> Optional[int]:
    try:
        return int(_obj)
    except Exception:
        return None


def secondaries_suffix(cap_secondaries: bool) -> Callable[[int], str]:
    if cap_secondaries:
        return lambda score: f" ({MAX_SECONDARY_POINTS} max)" if score > MAX_SECONDARY_POINTS else ""
    else:
        return lambda score: ""
