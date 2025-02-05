from __future__ import annotations

import logging
import re

from typing import Optional, List

from lxml import objectify
from lxml.objectify import ObjectifiedElement

from .utils import is_upgrade
from .extensions import FormatterOptions

logging.basicConfig()


class ForceView:
    def __init__(self, force: objectify.ObjectifiedElement, options: FormatterOptions):
        self.options = options
        self.pts = 0
        self.catalogue = force.get("catalogueName", "")

        self.detachment: str = force.get("name", None)
        if self.detachment is None:
            self.detachment = "Unparsed Detachment"
            logging.error(f"Detachment name is not found.")
        self.logger = logging.getLogger(f'ForceView - {self.detachment}')
        self.logger.setLevel(logging.DEBUG)

        force = force.selections.getchildren()
        self.detachment_choice = ""

        self.enumerated_unit_categories = {
            "Epic Hero": ("EH", []),
            "Character": ("CH", []),
            "Battleline": ("BL", []),
            "Infantry": ("IN", []),
            "Swarm": ("SW", []),
            "Mounted": ("MO", []),
            "Beast": ("BE", []),
            "Monster": ("MS", []),
            "Vehicle": ("VE", []),
            "Drone": ("DR", []),
            "Dedicated Transport": ("DT", []),
            "Fortification": ("FT", []),
            "Allied Units": ("AU", []),
        }

        self.__dispatch_selections(force)

    def __dispatch_selections(self, force: List[ObjectifiedElement]) -> None:
        for selection in force:
            if self.__is_of_type(selection, "Configuration", primary=True):
                self.__dispatch_configuration(selection)
            else:
                for key, (_, storage) in self.enumerated_unit_categories.items():
                    if self.__is_of_type(selection, key, primary=True):
                        storage.append(self.__parse_unit(selection))
                        break

    @staticmethod
    def __is_of_type(selection: ObjectifiedElement, category_name: str, primary: Optional[bool] = None) -> bool:
        primary = str(primary).lower()
        return any(
            category.get("name", "") == category_name and
            (primary == 'none' or category.get("primary", "") == primary)
            for category in selection.categories.getchildren()
        )

    def __dispatch_configuration(self, selection: ObjectifiedElement):
        if selection.get("name", "") in {
            "Battle Size",
            "Show/Hide Options",
        } or selection.get("name", "").startswith("Show "):
            # not interesting
            return

        if selection.get("name", "") in {
            "Detachment",
            "Detachment Choice",
        }:
            children = selection.selections.getchildren()
            if len(children):
                self.detachment_choice = children[0].get("name", "")
            return

        self.logger.error(f"Unknown unparsed item during configuration dispatching.", extra={"40k_item": selection.get('name', None)})

    def __recursive_cost_search(self, unit: objectify.ObjectifiedElement) -> int:
        total_cost_pts = 0
        for cost in unit.iter(tag="{*}cost"):
            name = cost.get("name", "").lower().strip()
            if name == "pts":
                total_cost_pts += int(float(cost.get("value", 0)))

        self.pts += total_cost_pts
        return total_cost_pts

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
                if name == "<Unparsed selection>":
                    logging.error(f"Selection name is not found.", extra={"40k_selection": element})
                name, number = self.__parse_multiplied_unit(name, number)
                elements_inside = self.__enumerate_all_selections(element, modifier=number * modifier)

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
            'cost': self.__recursive_cost_search(unit),
            'link': unit
        }
        if result['name'] == "Unparsed Model Name":
            logging.error(f"Unit name is not found.", extra={"40k_unit": unit})
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
