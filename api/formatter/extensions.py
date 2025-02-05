import logging
from dataclasses import dataclass, fields
from typing import Optional

from lxml.objectify import ObjectifiedElement

from .utils import is_upgrade, try_parse_int

logging.basicConfig()
logger = logging.getLogger("Extensions")
logger.setLevel(logging.DEBUG)

PROFILE_WOUNDS_POSITION = 3


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
        self.hide_basic_selections = self.hide_basic_selections == 'on'
        self.show_secondaries = self.show_secondaries == 'on'
        self.remove_costs = self.remove_costs == 'on'
        self.show_model_count = self.show_model_count == 'on'

        if self.hide_basic_selections:
            self.selector_checker = BasicSelectorChecker()


class BasicSelectorChecker:

    # oh well here we go again
    # problem: some selections in bsdata have to be visible but are upgrades with no cost (e.g., Chaos icon)
    dirty_hacks = [
        "Chaos icon",
    ]

    @staticmethod
    def is_basic(child: ObjectifiedElement):
        selection_name = child.get('name', "")
        if selection_name in BasicSelectorChecker.dirty_hacks:
            return False
        if "warlord" in selection_name.lower():
            return False  # 'warlord' is never a basic selection

        if child['link'].attrib['type'] == 'model':
            return False  # show all models

        result = "entryGroupId" in child['link'].attrib  # if it is a part of selection group - it is not basic
        return not result

    def clean_obligatory_selections(self, force: 'ForceView', result: dict) -> dict:
        result['children'] = [
            self.clean_obligatory_selections(force, child) for child in result['children']
            if not force.options.selector_checker.is_basic(child)
        ]
        return result


def add_double_whitespaces(formatted_roster: str) -> str:
    return '\n'.join(x + '  ' for x in formatted_roster.split('\n'))


def number_of_units(roster: 'RosterView') -> int:
    result = 0
    for force in roster.forces:
        for key, value in force.enumerated_unit_categories.items():
            result += len(value[1])
    return result


def count_secondaries(roster: 'RosterView') -> dict:
    return {
        'characters': __count_assasination(roster),
        'bring it down': __count_bring_it_down(roster),
    }


def __check_unit_category(
        selection: ObjectifiedElement,
        category_name: str,
):
    # check unit categories
    if hasattr(selection, 'categories'):
        for category in selection.categories.getchildren():
            if category.get("name", "") == category_name:
                return True

    # check categories of all selections
    if hasattr(selection, 'selections'):
        for children in selection.selections.getchildren():
            if __check_unit_category(children, category_name):
                return True

    return False


def __count_assasination(roster: 'RosterView') -> (int, int):
    """
    Returns total character units and models
    :return: (units, models)
    """
    units = 0
    models = 0
    for force in roster.forces:
        categories = [x[1] for x in force.enumerated_unit_categories.values()]

        for category in categories:
            for unit in category:
                if __check_unit_category(unit['link'], 'Character'):
                    debug_string = f'Unit: {unit["name"]} - Character'
                    logger.debug(debug_string)
                    roster.debug_info += debug_string + "\n"
                    units += 1

                    # calculate models
                    if not hasattr(unit['link'], 'selections'):
                        models += 1
                    else:
                        models_found = 0
                        for selection in unit['link'].selections.getchildren():
                            if __check_unit_category(selection, 'Character'):
                                current_models = try_parse_int(selection.get('number', 1)) or 1
                                models_found += current_models
                                models += current_models
                                debug_string = f'Models: {selection.get("name", "Unknown Name")} - ' \
                                               f'Character - Number: {current_models}'
                                logger.debug(debug_string)
                                roster.debug_info += debug_string + "\n"
                        if models_found == 0:
                            current_models = try_parse_int(unit.get('models', 1)) or 1
                            debug_string = f'Models: {unit.get("name", "Unknown Name")} - ' \
                                           f'Character - Number: {current_models} - Whole Unit is a Character'
                            logger.debug(debug_string)
                            roster.debug_info += debug_string + "\n"
                            models += current_models

    return units, models


def __count_bring_it_down(roster: 'RosterView') -> (int, int):
    """
    Return models and points
    :return: models, points
    """

    def get_wounds_from_profiles(unit: ObjectifiedElement) -> Optional[int]:
        profiles = [
            x for x in unit['link'].profiles.getchildren() if
            x.get("typeName", None) == 'Unit' and
            hasattr(x, 'characteristics') and
            try_parse_int(x.characteristics.getchildren()[PROFILE_WOUNDS_POSITION]) is not None
        ]

        if not profiles:
            return None

        return int(profiles[0].characteristics.getchildren()[PROFILE_WOUNDS_POSITION])

    def wounds_to_points(_wounds: int) -> int:
        if _wounds <= 9:
            return 0
        elif 10 <= _wounds <= 14:
            return 1
        elif 15 <= _wounds <= 19:
            return 2
        else:
            return 3

    points = 0
    models = 0
    for force in roster.forces:
        categories = [
            *[x[1] for x in force.enumerated_unit_categories.values()]
        ]
        for category in categories:
            for unit in category:
                if __check_unit_category(unit['link'], 'Monster') or __check_unit_category(unit['link'], 'Vehicle'):
                    if is_upgrade(unit['link']):
                        continue

                    # if object have profile with Unit type

                    if unit['link'].get('type', None) == 'model':
                        wounds = get_wounds_from_profiles(unit)
                        if not wounds:
                            continue
                        debug_string = f'Bring It Down: {unit["name"]} - 1 models - {wounds} wounds'
                        logger.debug(debug_string)
                        roster.debug_info += debug_string + '\n'
                        points += wounds_to_points(wounds) + 2
                        models += 1
                        continue

                    # otherwise - let's count it as a unit
                    # thanks to mistakes in BS database and people not prioritizing fixing them

                    # 2 variants:
                    # either unit has profiles
                    # or each selection in the unit

                    # variant 1
                    if hasattr(unit['link'], 'profiles'):
                        wounds = get_wounds_from_profiles(unit)
                        if wounds:
                            debug_string = f'Bring It Down: {unit["name"]} - {unit["models"]} models - {wounds} wounds'
                            logger.debug(debug_string)
                            roster.debug_info += debug_string + '\n'
                            wtp = wounds_to_points(wounds) + 2
                            wtp *= unit['models']
                            points += wtp
                            models += unit['models']
                            continue

                    # variant 2
                    for target in [x for x in unit['children'] if not is_upgrade(x['link'])]:
                        wounds = get_wounds_from_profiles(target)
                        if not wounds:
                            continue
                        models_count = target.get('number', 1)
                        debug_string = f'Bring It Down: {unit["name"]} - {models_count} models - {wounds} wounds'
                        logger.debug(debug_string)
                        roster.debug_info += debug_string + '\n'
                        points += (wounds_to_points(wounds) + 2) * models_count
                        models += models_count
    return models, points
