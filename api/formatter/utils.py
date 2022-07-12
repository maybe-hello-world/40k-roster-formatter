import logging
from typing import Optional, List

from lxml.objectify import ObjectifiedElement


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
    """
    if _object.get('type', None) == 'model':
        return False
    if _object.get('type', None) == 'unit':
        return False

    if hasattr(_object, 'profiles'):
        for profile in _object.profiles.getchildren():
            if profile.get('typeName', None) == 'Unit':
                logging.info(f"{_object.get('name', 'Unknown object')} is model/unit despite being marked as upgrade")
                return False

    return True


def try_parse_int(_obj) -> Optional[int]:
    try:
        return int(_obj)
    except Exception:
        return None
