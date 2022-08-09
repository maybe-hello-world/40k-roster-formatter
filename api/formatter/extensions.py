import logging
import os
import glob
from dataclasses import dataclass, fields
from typing import Optional

from yaml import load, FullLoader
from lxml.objectify import ObjectifiedElement

from .utils import is_upgrade, try_parse_int

logging.basicConfig()
logger = logging.getLogger("Extensions")
logger.setLevel(logging.DEBUG)

MAX_SECONDARY_POINTS = 15


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
    def __init__(self):
        self.database = dict()

        # load general selections
        with open(os.path.join("formatter", "res", "basic_selections", "general.yml"), "r") as f:
            data = load(f, Loader=FullLoader)
            self.database['general'] = set(data)

        files = glob.glob(os.path.join("formatter", "res", "basic_selections", "*.yml"))
        files = set(files) - {os.path.join("formatter", "res", "basic_selections", "general.yml")}
        for file in files:
            with open(file, "r") as f:
                data = load(f, Loader=FullLoader)
                self.database[data['faction']] = data['selections']

    def is_basic(self, catalogue: str, holder_name: str, selection_name: str):
        if "warlord" in selection_name.lower():
            return False  # 'warlord' is never a basic selection

        # check in the general catalogue
        if selection_name.lower() in {x.lower() for x in self.database.get('general', set())}:
            return True

        # check in the exact catalogue
        if selection_name.lower() in {x.lower() for x in self.database.get(catalogue, {}).get(holder_name, {})}:
            return True

        # check if everything should be omitted here
        if "*" in self.database.get(catalogue, {}).get(holder_name, {}):
            return True

        # remove last dash-separated word iteratively and check again
        # it would allow constructing catalogues like
        # "Imperium",
        # "Imperium - Adeptus Astartes",
        # and "Imperium - Adeptus Astartes - Iron Hands"
        dash_separated = catalogue.split('-')
        while len(dash_separated) > 1:
            dash_separated = dash_separated[:-1]
            catalogue = '-'.join(dash_separated).strip()
            if (
                    selection_name.lower() in {x.lower() for x in
                                               self.database.get(catalogue, {}).get(holder_name, {})} or
                    "*" in self.database.get(catalogue, {}).get(holder_name, {})
            ):
                return True

        return False

    def clean_obligatory_selections(self, force: 'ForceView', result: dict) -> dict:
        result['children'] = [
            self.clean_obligatory_selections(force, child) for child in result['children']
            if not force.options.selector_checker.is_basic(force.catalogue, result['name'], child.get("name"))
        ]
        return result


def add_double_whitespaces(formatted_roster: str) -> str:
    return '\n'.join(x + '  ' for x in formatted_roster.split('\n'))


def number_of_units(roster: 'RosterView') -> int:
    result = 0
    for force in roster.forces:
        result += len(force.no_force_org)
        result += len(force.agents_of_imperium)
        result += len(force.supreme_commander)
        for key, value in force.enumerated_unit_categories.items():
            result += len(value[1])
    return result


def count_secondaries(roster: 'RosterView') -> dict:
    return {
        'assassination': __count_assasination(roster),
        'bring it down': __count_bring_it_down(roster),
        'no prisoners': __count_no_prisoners(roster),
        'abhor the witch': __count_abhor_the_witch(roster),
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


def __count_assasination(roster: 'RosterView') -> int:
    points = 0
    for force in roster.forces:
        categories = [
            force.no_force_org,
            force.supreme_commander,
            force.agents_of_imperium,
            *[x[1] for x in force.enumerated_unit_categories.values()]
        ]

        for category in categories:
            for unit in category:
                if __check_unit_category(unit['link'], 'Character'):
                    debug_string = f'Assassination: {unit["name"]} - Character'
                    logger.debug(debug_string)
                    roster.debug_info += debug_string + "\n"
                    points += 1

    points *= 3
    points += 1  # Warlord
    return min(points, MAX_SECONDARY_POINTS)


def __count_bring_it_down(roster: 'RosterView') -> int:
    def get_wounds_from_profiles(unit: ObjectifiedElement) -> Optional[int]:
        profiles = [
            x for x in unit['link'].profiles.getchildren() if
            x.get("typeName", None) == 'Unit' and
            hasattr(x, 'characteristics') and
            try_parse_int(x.characteristics.getchildren()[5]) is not None
        ]

        if not profiles:
            return None

        return int(profiles[0].characteristics.getchildren()[5])



    def wounds_to_points(_wounds: int) -> int:
        if _wounds <= 9:
            return 1
        elif 10 <= _wounds <= 14:
            return 2
        elif 15 <= _wounds <= 19:
            return 3
        else:
            return 4

    points = 0
    for force in roster.forces:
        categories = [
            force.no_force_org,
            force.supreme_commander,
            force.agents_of_imperium,
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
                        points += wounds_to_points(wounds)
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
                            wtp = wounds_to_points(wounds)
                            wtp *= unit['models']
                            points += wtp
                            continue

                    # variant 2
                    for target in [x for x in unit['children'] if not is_upgrade(x['link'])]:
                        wounds = get_wounds_from_profiles(target)
                        if not wounds:
                            continue
                        debug_string = f'Bring It Down: {unit["name"]} - 1 models - {wounds} wounds'
                        logger.debug(debug_string)
                        roster.debug_info += debug_string + '\n'
                        points += wounds_to_points(wounds)
    return min(points, MAX_SECONDARY_POINTS)


def __count_no_prisoners(roster: 'RosterView') -> int:
    points = 0
    tally = 0
    for force in roster.forces:
        categories = [
            force.no_force_org,
            force.supreme_commander,
            force.agents_of_imperium,
            *[x[1] for x in force.enumerated_unit_categories.values()]
        ]

        for category in categories:
            for unit in category:
                if (
                        __check_unit_category(unit['link'], 'Monster') or
                        __check_unit_category(unit['link'], 'Vehicle') or
                        __check_unit_category(unit['link'], 'Character')
                ):
                    # check 1st level descendants - if they have own categories without vehicle/monster - add them
                    for child in unit['children']:
                        if (
                                child['link'].get('type', None) == 'model' and
                                hasattr(child['link'], 'categories') and
                                len(child['link'].categories.getchildren()) > 0 and
                                not (__check_unit_category(child['link'], 'Monster') or
                                     __check_unit_category(child['link'], 'Vehicle') or
                                     __check_unit_category(child['link'], 'Character'))
                        ):
                            if not hasattr(child['link'], 'profiles'):
                                continue
                            profiles = [
                                x for x in child['link'].profiles.getchildren() if
                                x.get('typeName', None) == 'Unit'
                            ]
                            wounds = profiles[0].characteristics.getchildren()[5]
                            tally += wounds * child['number']
                            debug_string = f'No Prisoners: {child["number"]}x{child["name"]} - {wounds} wounds - current tally: {tally}'
                            logger.debug(debug_string)
                            roster.debug_info += debug_string + '\n'

                else:
                    profiles = []
                    if hasattr(unit['link'], 'profiles'):
                        profiles = [
                            x for x in unit['link'].profiles.getchildren()
                            if x.get('typeName', None) == 'Unit'
                        ]

                    if not profiles:
                        # then each selection in the unit has own profile and just count them
                        for model in (x for x in unit['children'] if not is_upgrade(x['link'])):
                            profiles = [x for x in model['link'].profiles.getchildren() if
                                        x.get('typeName', None) == 'Unit']
                            if not profiles:
                                # then it's damn unit of units of models (hello, seer council)
                                for submodel in (x for x in model['children'] if not is_upgrade(x['link'])):
                                    profiles = [x for x in submodel['link'].profiles.getchildren() if
                                                x.get('typeName', None) == 'Unit']
                                    if not profiles:
                                        continue
                                    wounds = profiles[0].characteristics.getchildren()[5]
                                    tally += wounds * model['number']
                                    debug_string = f'No Prisoners: {model["number"]}x{model["name"]} - {wounds} wounds - current tally: {tally}'
                                    logger.debug(debug_string)
                                    roster.debug_info += debug_string + '\n'
                                pass
                            else:
                                wounds = profiles[0].characteristics.getchildren()[5]
                                tally += wounds * model['number']
                                debug_string = f'No Prisoners: {model["number"]}x{model["name"]} - {wounds} wounds - current tally: {tally}'
                                logger.debug(debug_string)
                                roster.debug_info += debug_string + '\n'
                    else:
                        children_with_profiles = []
                        for child in unit['children']:
                            if (
                                    hasattr(child['link'], 'profiles') and
                                    len([x for x in child['link'].profiles.getchildren() if x.get('typeName', None) == 'Unit'])
                            ):
                                children_with_profiles.append(child)

                        # if no children has their own Unit profiles - just number of models * wounds in profiles
                        models = unit['models'] - len(children_with_profiles)
                        wounds = profiles[0].characteristics.getchildren()[5]
                        tally += wounds * models
                        debug_string = f'No Prisoners: {models}x{unit["name"]} - {wounds} wounds - current tally: {tally}'
                        logger.debug(debug_string)
                        roster.debug_info += debug_string + '\n'

                        for child in children_with_profiles:
                            # add them separately
                            children_profile = [x for x in child['link'].profiles.getchildren() if x.get('typeName', None) == 'Unit']
                            wounds = children_profile[0].characteristics.getchildren()[5]
                            tally += wounds * child['number']
                            debug_string = f'No Prisoners: {child["number"]}x{child["name"]} - {wounds} wounds - current tally: {tally}'
                            logger.debug(debug_string)
                            roster.debug_info += debug_string + '\n'

    if 50 <= tally <= 99:
        points = 1
    if tally >= 100:
        points = 2
    tally = tally // 10
    return min(points + tally, MAX_SECONDARY_POINTS)


def __count_abhor_the_witch(roster: 'RosterView') -> int:
    points = 0
    for force in roster.forces:
        categories = [
            force.no_force_org,
            force.supreme_commander,
            force.agents_of_imperium,
            *[x[1] for x in force.enumerated_unit_categories.values()]
        ]

        for category in categories:
            for unit in category:
                if __check_unit_category(unit['link'], 'Psyker'):
                    if __check_unit_category(unit['link'], 'Character'):
                        debug_string = f'Abhor The Witch: {unit["name"]} - Psyker & Character'
                        logger.debug(debug_string)
                        roster.debug_info += debug_string + "\n"
                        points += 3
                    else:
                        debug_string = f'Abhor The Witch: {unit["name"]} - Psyker'
                        logger.debug(debug_string)
                        roster.debug_info += debug_string + "\n"
                        points += 2
    return min(points, MAX_SECONDARY_POINTS)
