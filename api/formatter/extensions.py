import os
import glob
from yaml import load, FullLoader
from lxml.objectify import ObjectifiedElement

MAX_SECONDARY_POINTS = 15


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
            return __check_unit_category(children, category_name)

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
            points += sum(__check_unit_category(x['link'], 'Character') for x in category)

    points *= 3
    points += 1  # Warlord
    return min(points, MAX_SECONDARY_POINTS)


def __count_bring_it_down(roster: 'RosterView') -> int:
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
                    if unit['link'].get('type', None) == 'model':
                        profiles = [x for x in unit['link'].profiles.getchildren() if
                                    x.get("typeName", None) == 'Unit']
                        if not profiles:
                            continue
                        wounds = profiles[0].characteristics.getchildren()[5]  # wounds is 6th
                        points += wounds_to_points(wounds)

                    if unit['link'].get('type', None) == 'unit':
                        # 2 variants:
                        # either unit has profiles
                        # or each selection in the unit

                        # variant 1
                        if hasattr(unit['link'], 'profiles'):
                            profiles = [x for x in unit['link'].profiles.getchildren() if
                                        x.get("typeName", None) == 'Unit']
                            if not profiles:
                                continue
                            wounds = profiles[0].characteristics.getchildren()[5]  # wounds is 6th
                            wtp = wounds_to_points(wounds)
                            wtp *= unit['models']
                            points += wtp

                        # variant 2
                        else:
                            for target in [x for x in unit['children'] if x['link'].get('type', None) == 'model']:
                                profiles = [x for x in target['link'].profiles.getchildren() if
                                            x.get("typeName", None) == 'Unit']
                                if not profiles:
                                    continue
                                wounds = profiles[0].characteristics.getchildren()[5]  # wounds is 6th
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

                            print(f'unit: {child["number"]}x{child["name"]}, wounds: {wounds}, tally: {tally}')

                else:
                    for model in (x for x in unit['children'] if x['link'].get('type', None) == 'model'):
                        profiles = [x for x in model['link'].profiles.getchildren() if
                                    x.get('typeName', None) == 'Unit']
                        wounds = profiles[0].characteristics.getchildren()[5]
                        tally += wounds * model['number']
                        print(f'unit: {model["number"]}x{model["name"]}, wounds: {wounds}, tally: {tally}')
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
                    points += 2
                    if __check_unit_category(unit['link'], 'Character'):
                        points += 1

    return min(points, MAX_SECONDARY_POINTS)
