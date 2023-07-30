import logging
from typing import Optional

from lxml.objectify import ObjectifiedElement


class FormatterException(Exception):
    pass


def is_upgrade(_object: ObjectifiedElement) -> bool:
    """
    Because 'type'=='upgrade' not always mean that it's upgrade
    https://github.com/bsdata/wh40k/issues/11182

    New round of problems: some models in units are marked as 'upgrade' and do not have profiles.
    Let's keep the list of such units here as there no other way to fix this (except fixing BS data, of course)
    """

    # 10th edition, empty yet
    damn_dirty_hacks = []

    if _object.get('type', None) == 'model':
        return False
    if _object.get('type', None) == 'unit':
        return False

    if hasattr(_object, 'profiles'):
        for profile in _object.profiles.getchildren():
            if profile.get('typeName', None) == 'Unit':
                logging.info(
                    f"{_object.get('name', 'Unknown object')} is model/unit despite being marked as upgrade",
                )
                return False

    for hack in damn_dirty_hacks:
        if _object.get('name', '').startswith(hack):
            logging.warning("Still using dirty hack for is_upgrade", extra={'40k_object': _object})
            return False

    return True


def try_parse_int(_obj) -> Optional[int]:
    try:
        return int(_obj)
    except Exception:
        return None
