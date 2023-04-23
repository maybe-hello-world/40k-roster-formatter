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

        name: str = force.get("name", None)
        if name is None:
            name = "Unparsed Detachment ?CP"
            logging.error(f"Detachment name is not found.")
        self.cp = 0
        if "Detachment" in name:
            name, cp = name.rsplit(" ", maxsplit=1)
            cp = cp.lower().strip()
            try:
                self.cp = int(remove_suffix(cp, "cp"))
            except ValueError:
                self.cp = 0
        self.detachment = name
        self.logger = logging.getLogger(f'ForceView - {self.detachment}')
        self.logger.setLevel(logging.DEBUG)

        force = force.selections.getchildren()
        self.army_of_renown = None
        self.faction = ""

        self.stratagems = []
        self.no_force_org = []
        self.agents_of_imperium = []
        self.supreme_commander = []

        self.enumerated_unit_categories = {
            "HQ": ("HQ", []),
            "Troops": ("TR", []),
            "Elites": ("EL", []),
            "Fast Attack": ("FA", []),
            "Heavy Support": ("HS", []),
            "Flyer": ("FL", []),
            "Dedicated Transport": ("DT", []),
            "Lord of War": ("LOW", []),
            "Fortification": ("FT", []),
        }

        self.__dispatch_selections(force)

    def __dispatch_selections(self, force: List[ObjectifiedElement]) -> None:
        for selection in force:
            if self.__is_of_type(selection, "Stratagems"):
                self.stratagems.append(self.__parse_stratagem(selection))
            elif self.__is_of_type(selection, "No Force Org Slot"):
                self.no_force_org.append(self.__parse_unit(selection))
            elif self.__is_of_type(selection, "Agent of the Imperium", primary=True):
                self.agents_of_imperium.append(self.__parse_unit(selection))
            elif self.__is_of_type(selection, 'Primarch | Daemon Primarch | Supreme Commander', primary=True):
                self.supreme_commander.append(self.__parse_unit(selection))
            elif self.__is_of_type(selection, "Configuration", primary=True):
                self.__dispatch_configuration(selection)
            else:
                for key, (_, storage) in self.enumerated_unit_categories.items():
                    if self.__is_of_type(selection, key):
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
            "Detachment Command Cost",
            "Gametype",
            "Game Type",
            "Unit Filter",
            "Use Beta Rules",
            "Arks of Omen Compulsory Type",
            "Questor Allegiance",
            "Militarum Tempestus Detachment",
            "Raiding Forces - CP Refund",
            "Crusade Tally",
            "Daemonic Pact",
        }:
            # not interesting
            return

        if (
                selection.get("name", "").lower().strip().startswith("army of renown") or
                selection.get("name", "") in
                {
                    "Terminus Est Assault Force",
                }
        ):
            self.army_of_renown = selection.get('name', None)
            if self.army_of_renown is None:
                self.army_of_renown = "Unparsed Army of Renown"
                logging.error(f"Army of Renown name is not found.", extra={"40k_selection": selection})
            return

        if "Reference" in selection.get("name", ""):
            return

        if not self.faction:
            self.__parse_faction(selection)
            return

        self.logger.error(f"Unknown unparsed item during configuration dispatching.", extra={"40k_item": selection.get('name', None)})

    def __parse_faction(self, faction: ObjectifiedElement):
        if "selections" not in dir(faction) or not (faction := faction.selections.getchildren()):
            # Leave it empty - usually that means that army has only one faction (black templars, deathwatch, etc)
            self.faction = ""
            return

        faction_name = faction[0].get("name", None)
        if faction_name is None:
            faction_name = "Unparsed Faction"
            logging.error(f"Faction name is not found.", extra={"40k_faction": faction})

        addons = [x.get("name", "Unparsed Subfaction") for x in faction[0].iterdescendants(tag="{*}selection")]
        if addons:
            faction_name = f"{faction_name} ({', '.join(addons)})"
            for addon in addons:
                if addon == "Unparsed Subfaction":
                    logging.error(f"Subfaction name is not found.", extra={"40k_faction": faction})
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
            'cost': self.__get_unit_cost(unit),
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

    @staticmethod
    def __parse_stratagem(stratagem: objectify.ObjectifiedElement) -> str:
        name = stratagem.get("name", "Unparsed Stratagem")
        if name == "Unparsed Stratagem":
            logging.error(f"Stratagem name is not found.", extra={"40k_stratagem": stratagem})
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
