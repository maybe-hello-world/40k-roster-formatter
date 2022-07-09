from dataclasses import dataclass, fields
from typing import Optional, List

from lxml.objectify import ObjectifiedElement

from .extensions import BasicSelectorChecker


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


@dataclass(repr=True, eq=True, order=True)
class FormatterOptions:
    hide_basic_selections: bool = False
    show_secondaries: bool = False
    remove_costs: bool = False
    show_model_count: bool = False

    def __init__(self, **kwargs):
        class_fields = {field.name for field in fields(self)}
        for key, value in kwargs.items():
            if key in class_fields:
                setattr(self, key, value)

        self.__post_init__()

    def __post_init__(self):
        if self.hide_basic_selections == 'on':
            self.hide_basic_selections = True
            self.selector_checker = BasicSelectorChecker()

        if self.show_secondaries == 'on':
            self.show_secondaries = True

        if self.remove_costs == 'on':
            self.remove_costs = True

        if self.show_model_count == 'on':
            self.show_model_count = True
