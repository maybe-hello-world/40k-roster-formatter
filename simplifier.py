from __future__ import annotations

from typing import Optional
from zipfile import ZipFile

from lxml import objectify
from lxml.objectify import ObjectifiedElement

from collections import Counter


class SimplifierException(Exception):
    pass


def single_children_by_name(children: list[ObjectifiedElement], name: str) -> Optional[ObjectifiedElement]:
    children = [x for x in children if x.get("name", None) == name]
    if len(children) == 1:
        return children[0]
    else:
        return None


class ForceView:
    def __init__(self, force: objectify.ObjectifiedElement):
        self.pts = 0
        self.pl = 0

        name: str = force.get("name", "Unparsed Detachment ?CP")
        if "Detachment" in name:
            name, cp = name.rsplit(" ", maxsplit=1)
            self.cp = int(cp.lower().strip().removesuffix("cp"))
        self.detachment = name
        self.__parse_faction(force)

        force = force.selections.getchildren()

        self.non_enumerated_units = {
            "Stratagems": [],
            "No Force Org Slot": [],
            "Agent of the Imperium": []
        }

        # parse stratagems
        self.non_enumerated_units['Stratagems'].extend([
            self.__parse_stratagem(x) for x
            in self.__get_selections_of_category(force, "Stratagems")
        ])

        for key in ["No Force Org Slot", "Agent of the Imperium"]:
            self.non_enumerated_units[key].extend([
                self.__parse_units(unit) for unit
                in self.__get_selections_of_category(force, key)
            ])

        self.enumerated_units = {
            "HQ": ["HQ", []],
            "Troops": ["TR", []],
            "Elites": ["EL", []],
            "Fast Attack": ["FA", []],
            "Heavy Support": ["HS", []],
            "Flyer": ["FL", []],
            "Dedicated Transport": ["DT", []]
        }

        for key, (_, storage) in self.enumerated_units.items():
            storage.extend([
                self.__parse_units(unit) for unit
                in self.__get_selections_of_category(force, key)
            ])

    @staticmethod
    def __get_selections_of_category(
            selections: list[ObjectifiedElement],
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

        selections = [
            x for x in selections
            if x.get("name", "") not in {
                "Battle Size", "Detachment Command Cost", "Gametype", "Unit Filter", "Use Beta Rules"
            }
        ]

        if len(selections) != 1:
            self.faction = "Unparsed Faction"
            return

        faction = selections[0]
        faction = faction.selections.getchildren()
        if not faction:
            self.faction = "Unparsed Faction"
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
        for cost in unit.iter(tag="{*}cost"):
            name = cost.get("name", "").lower().strip()
            if name == "pts":
                total_cost_pts += int(float(cost.get("value", 0)))
            elif name == "pl":
                total_cost_pl += int(float(cost.get("value", 0)))
            elif name == "cp":
                total_cost_cp += int(float(cost.get("value", 0)))

        return total_cost_pts, total_cost_pl, total_cost_cp

    def __get_unit_cost(self, unit: objectify.ObjectifiedElement) -> str:
        cost_pts, cost_pl, cost_cp = self.__recursive_cost_search(unit)
        self.pts += cost_pts
        self.pl += cost_pl

        total_cost = f"[{cost_pts} pts, {cost_pl} PL"
        total_cost += f", {cost_cp} CP" if cost_cp else ""
        total_cost += "]"
        return total_cost

    def __enumerate_all_selections(self, selection: objectify.ObjectifiedElement) -> str:
        children = selection.iterchildren(tag="{*}selections")
        output = []
        for child in children:
            for element in child.getchildren():
                number = int(element.get("number", 1))
                name: str = element.get("name", "<Unparsed selection>")
                if number > 1:
                    name = f"{number}x{name}"

                elements_inside = self.__enumerate_all_selections(element)
                if elements_inside:
                    name = f"{name} ({elements_inside})"

                output.append(name)

        counter = Counter(output)
        output = [f"{'' if value == 1 else str(value) + 'x'}{key}" for key, value in counter.items()]
        return ', '.join(output)

    def __parse_units(self, unit: objectify.ObjectifiedElement) -> str:
        name = unit.get("name", "Unparsed Model Name")
        selections = self.__enumerate_all_selections(unit)
        cost = self.__get_unit_cost(unit)
        return f"{name}: {selections} {cost}" if selections else f"{name} {cost}"

    @staticmethod
    def __parse_stratagem(stratagem: objectify.ObjectifiedElement) -> str:
        name = "- " + stratagem.get("name", "Unparsed Stratagem").removeprefix("Stratagem: ")
        cost = int(float(single_children_by_name(stratagem.costs.getchildren(), "CP").get("value", "0.0")))
        return f"{name} ({cost} CP)"

    def __str__(self):
        header = f"== {self.faction} {self.detachment} == {self.cp} CP, {self.pts} pts, {self.pl} PL"

        for key, value in self.non_enumerated_units.items():
            if value:
                value.insert(0, f"{key}:")
                value.append("")

        for key, value in self.enumerated_units.items():
            if value[1]:
                self.enumerated_units[key][1] = [f"{value[0]}{i + 1}: {v}" for i, v in enumerate(value[1])] + [""]

        non_enumerated = ['\n'.join(x) for x in self.non_enumerated_units.values() if x]
        enumerated = ['\n'.join(x[1]) for x in self.enumerated_units.values() if x[1]]

        return '\n'.join([
            header,
            "",
            *non_enumerated,
            *enumerated,
        ])


class RosterView:
    def __str__(self):
        header = '\n'.join([
            f"PLAYER: ",
            f"Army name: {self.name}",
            f"Factions used: {', '.join(self.factions)}",
            f"Command Points: {self.cp_total}",
            f"Total cost: {self.pts_total} pts, {self.pl_total} PL",
            f"Reinforcement Points: {self.reinf_points}",
            "-" * 10,
            "",
        ])

        footer = ""

        return '\n'.join(str(x) for x in [header, *self.forces, footer])

    @staticmethod
    def __extract(input_file, zipped: bool = True) -> dict:
        if zipped:
            input_file = ZipFile(input_file)
            return {name: input_file.read(name) for name in input_file.namelist()}
        else:
            with open(input_file, 'rt') as f:
                input_file = f.read().encode('utf-8')
            return {"default": input_file}

    @staticmethod
    def __read_xml(content: dict) -> objectify.ObjectifiedElement:
        if len(content) != 1:
            raise SimplifierException(f"Unknown structure of provided rosz archive. Content: {content.keys()}")

        name: str = next(iter(content))
        roster: objectify.ObjectifiedElement = objectify.fromstring(content[name])

        return roster

    def __set_reinf_points(self, roster: objectify.ObjectifiedElement):
        pts_limit = [
            x.costLimit.get("value")
            for x in roster.iter(tag='{*}costLimits')
            if x.costLimit.get("name", "") == "pts"
        ]
        pts_limit = int(float(pts_limit[0])) if pts_limit else 0
        reinf_points = pts_limit - self.pts_total
        self.reinf_points = str(reinf_points) if reinf_points > 0 else 'none'

    def __init__(self, filename: str, zipped: bool = True):
        roster = self.__read_xml(self.__extract(filename, zipped))
        self.name = roster.attrib.get("name", "")

        total_cost = {
            x.attrib['name'].strip(): int(float(x.attrib['value']))
            for x in roster.costs.iterchildren()
        }
        self.cp_total = total_cost.get("CP", 0)
        self.pl_total = total_cost.get("PL", 0)
        self.pts_total = total_cost.get("pts", 0)
        self.__set_reinf_points(roster)
        self.factions = set(x.attrib.get("catalogueName", "<ERROR: UNPARSED>") for x in roster.forces.iterchildren())

        forces = (x for x in roster.forces.iterchildren(tag="{*}force"))
        self.forces = [ForceView(x) for x in forces]


if __name__ == '__main__':
    filename = "data/ab.ros"
    result = RosterView(filename, False)
    print(result)
