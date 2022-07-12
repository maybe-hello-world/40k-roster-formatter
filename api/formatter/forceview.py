from __future__ import annotations

import logging
import re

from typing import Optional, List

from lxml import objectify
from lxml.objectify import ObjectifiedElement

from .utils import remove_prefix, remove_suffix, is_upgrade
from .extensions import FormatterOptions

logging.basicConfig()


class ForceView:
    def __init__(self, force: objectify.ObjectifiedElement, options: FormatterOptions):
        self.options = options
        self.pts = 0
        self.pl = 0
        self.cabal_points = 0
        self.cp_modifiers = []
        self.catalogue = force.get("catalogueName", "")
        self.__collect_cp_modifiers(force)

        name: str = force.get("name", "Unparsed Detachment ?CP")
        if "Detachment" in name:
            name, cp = name.rsplit(" ", maxsplit=1)
            cp = cp.lower().strip()
            self.cp = int(remove_suffix(cp, "cp"))
        else:
            self.cp = 0
        self.detachment = name
        self.__parse_faction(force)
        self.logger = logging.getLogger(f'ForceView - {self.detachment}')
        self.logger.setLevel(logging.DEBUG)

        force = force.selections.getchildren()
        self.army_of_renown = self.__parse_army_of_renown(force)

        self.stratagems = []
        self.no_force_org = []
        self.agents_of_imperium = []
        self.supreme_commander = []

        self.stratagems.extend([
            self.__parse_stratagem(x) for x
            in self.__get_selections_of_category(force, "Stratagems")
        ])

        self.no_force_org.extend([
            self.__parse_unit(unit) for unit
            in self.__get_selections_of_category(force, "No Force Org Slot")
        ])

        self.agents_of_imperium.extend([
            self.__parse_unit(unit) for unit
            in self.__get_selections_of_category(force, "Agent of the Imperium", primary=True)
        ])

        self.supreme_commander.extend([
            self.__parse_unit(unit) for unit
            in self.__get_selections_of_category(force, 'Primarch | Daemon Primarch | Supreme Commander', primary=True)
        ])

        self.enumerated_unit_categories = {
            "HQ": ["HQ", []],
            "Troops": ["TR", []],
            "Elites": ["EL", []],
            "Fast Attack": ["FA", []],
            "Heavy Support": ["HS", []],
            "Flyer": ["FL", []],
            "Dedicated Transport": ["DT", []],
            "Lord of War": ["LOW", []],
            "Fortification": ["FT", []],
        }

        for key, (_, storage) in self.enumerated_unit_categories.items():
            storage.extend([
                self.__parse_unit(unit) for unit
                in self.__get_selections_of_category(force, key)
            ])

    @staticmethod
    def __get_selections_of_category(
            selections: List[ObjectifiedElement],
            category_name: str,
            primary: Optional[bool] = None
    ):
        primary = str(primary).lower()

        return [
            x for x in selections
            if any(
                category.get("name", "") == category_name and
                (primary == 'none' or category.get("primary", "") == primary)
                for category in x.categories.getchildren()
            )
        ]

    def __parse_faction(self, force: objectify.ObjectifiedElement):
        selections = force.selections.getchildren()
        selections = self.__get_selections_of_category(selections, "Configuration", primary=True)

        # TODO: temporary solution, think how to get faction name more reliable
        selections = [
            x for x in selections
            if x.get("name", "") not in {
                "Battle Size", "Detachment Command Cost", "Gametype", "Unit Filter", "Use Beta Rules"
            }
        ]
        selections = [x for x in selections if "Reference" not in x.get("name", "")]

        if len(selections) == 0:
            self.faction = ""
            return

        faction = selections[0]  # if bigger than 1: let's hope chapter would be the first

        if "selections" not in dir(faction) or not (faction := faction.selections.getchildren()):
            # Leave it empty - usually that means that army has only one faction (black templars, deathwatch, etc)
            self.faction = ""
            return

        faction_name = faction[0].get("name", "Unparsed Faction")

        addons = [x.get("name", "Unparsed Subfaction") for x in faction[0].iterdescendants(tag="{*}selection")]
        if addons:
            faction_name = f"{faction_name} ({', '.join(addons)})"
        if len(faction) > 1:
            faction_name += " (" + ', '.join(x.get("name", "") for x in faction[1:]) + ")"

        self.faction = faction_name

    @staticmethod
    def __recursive_cost_search(unit: objectify.ObjectifiedElement) -> (int, int, int):
        total_cost_pts = 0
        total_cost_pl = 0
        total_cost_cp = 0
        total_cabal_points = 0
        for cost in unit.iter(tag="{*}cost"):
            name = cost.get("name", "").lower().strip()
            if name == "pts":
                total_cost_pts += int(float(cost.get("value", 0)))
            elif name == "pl":
                total_cost_pl += int(float(cost.get("value", 0)))
            elif name == "cp":
                total_cost_cp += int(float(cost.get("value", 0)))
            elif name == "cabal points":
                total_cabal_points += int(float(cost.get("value", 0)))

        return total_cost_pts, total_cost_pl, total_cost_cp, total_cabal_points

    def __get_unit_cost(self, unit: objectify.ObjectifiedElement) -> dict:
        cost_pts, cost_pl, cost_cp, cost_cabal_points = self.__recursive_cost_search(unit)
        self.pts += cost_pts
        self.pl += cost_pl
        self.cabal_points += cost_cabal_points

        return {
            'pts': cost_pts,
            'pl': cost_pl,
            'cp': cost_cp,
            'cabal': cost_cabal_points
        }

    @staticmethod
    def __parse_multiplied_unit(name: str, number: int) -> (str, int):
        """
        This function is a damn crutch as BS data developers sometimes create units
        like "2x MV1 Gun Drone" with number=1 (instead of correct version "MV1 Gun Drone" with number=2).

        So here we receive the name and current number and if name starts with "<number>x "
        then remove the prefix and return number * prefix

        :param name: unit's name
        :param number: amount of such units
        :return: if in prefix multiplier exists then Tuple[name without multiplier, number * prefix],
         original values otherwise
        """

        pattern = re.compile(r"(?P<multiplier>\d+)x (?P<unitname>.*)")
        if match := pattern.match(name):
            number *= int(match.group('multiplier'))
            name = match.group('unitname')
        return name, number

    def __enumerate_all_selections(self, selection: objectify.ObjectifiedElement, modifier: int = 1) -> List[dict]:
        children = selection.iterchildren(tag="{*}selections")
        output = []
        for child in children:
            for element in child.getchildren():
                number = int(element.get("number", 1))
                name: str = element.get("name", "<Unparsed selection>")
                name, number = self.__parse_multiplied_unit(name, number)
                elements_inside = self.__enumerate_all_selections(element, modifier=number * modifier)

                # if self.options.hide_basic_selections:
                #     if self.options.selector_checker.is_basic(self.catalogue, selection.get("name"), name):
                #         continue

                number //= modifier

                output.append(
                    {
                        'name': name,
                        'number': number,
                        'children': elements_inside,
                        'link': element,
                    }
                )

        return output

    def __parse_unit(self, unit: objectify.ObjectifiedElement) -> dict:
        result = {
            'name': unit.get("name", "Unparsed Model Name"),
            'children': self.__enumerate_all_selections(unit),
            'cost': self.__get_unit_cost(unit),
            'link': unit
        }
        result['models'] = self.__get_models_amount(result)

        return result

    def __get_models_amount(self, unit: dict) -> int:
        utype = unit['link'].get('type', 'model')
        if is_upgrade(unit['link']):
            return 0

        if utype == 'unit':
            number = sum(self.__get_models_amount(x) for x in unit['children'])
            self.logger.debug(f'get_models_amount: {unit["name"]}: {number}')
            return number

        if hasattr(unit, 'selection'):
            number = int(unit.selection.get('number', 1))
        else:
            number = int(unit.get('number', 1))
        if unit.get('children', None):
            number += sum(self.__get_models_amount(x) for x in unit['children'])
        self.logger.debug(f'get_models_amount: {unit["name"]}: {number}')
        return number

    @staticmethod
    def __parse_stratagem(stratagem: objectify.ObjectifiedElement) -> str:
        name = stratagem.get("name", "Unparsed Stratagem")
        name = remove_prefix(name, "Stratagem: ")
        _, _, cost, _ = ForceView.__recursive_cost_search(stratagem)
        return f"{name} ({cost} CP)"

    def __collect_cp_modifiers(self, force: objectify.ObjectifiedElement):
        for cost in force.iter(tag="{*}cost"):
            name = cost.get("name", "").lower().strip()
            if name == "cp":
                cp_cost = int(float(cost.get("value", 0)))
                if cp_cost != 0:
                    self.cp_modifiers.append(cp_cost)

    def __parse_army_of_renown(self, force: List[objectify.ObjectifiedElement]) -> Optional[str]:
        selections = self.__get_selections_of_category(force, "Configuration", primary=True)
        selections = [
            x
            for x in selections
            if x.get("name", "").lower().strip().startswith("army of renown")
               or x.get("name", "") in {"Terminus Est Assault Force"}
        ]
        if selections:
            return selections[0].get('name', 'Unparsed Army of Renown')
