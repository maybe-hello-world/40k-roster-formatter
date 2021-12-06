from __future__ import annotations
from zipfile import ZipFile
from dataclasses import dataclass

from lxml import objectify
from lxml.objectify import ObjectifiedElement


class SimplifierException(Exception):
    pass


class ForceView:
    PREFIX: str = "{http://www.battlescribe.net/schema/rosterSchema}"
    pts: int = 0
    cp: int = 0
    pl: int = 0
    faction: str = ""
    detachment: str = ""

    def __init__(self, force: objectify.ObjectifiedElement):
        name: str = force.get("name", "Unparsed Detachment ?CP")
        if "Detachment" in name:
            name, cp = name.rsplit(" ", maxsplit=1)
            self.cp = int(cp.lower().strip().removesuffix("cp"))
        self.detachment = name
        self.__parse_faction(force)

    def __check_primary(self, children: list[ObjectifiedElement], category_name: str, primary: bool = True) -> bool:
        primary = 'true' if primary else 'false'
        children = [x for x in children if x.tag == self.PREFIX + "category"]
        children = [x for x in children if x.get("primary", 'false') == primary]
        return len(children) == 1 and children[0].get("name", "") == category_name

    def __parse_faction(self, force: objectify.ObjectifiedElement):
        selections = force.selections.getchildren()
        selections = [
            x for x in selections
            if self.__check_primary(x.categories.getchildren(), "Configuration")
        ]

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
        elif len(faction) == 1:
            self.faction = faction[0].get("name", "Unparsed Faction")
        else:
            self.faction = (
                    faction[0].get("name", "Unparsed Faction") +
                    " (" + ', '.join(x.get("name", "") for x in faction[1:]) + ")"
            )

    def __str__(self):
        return '\n'.join([
            f"== {self.faction} {self.detachment} == {self.cp} CP, {self.pts} pts"
        ])


class RosterView:
    PREFIX = "{http://www.battlescribe.net/schema/rosterSchema}"

    def __str__(self):
        header = '\n'.join([
            f"PLAYER: ",
            f"Army name: {self.name}",
            f"Factions used: {', '.join(self.factions)}",
            f"Command Points: {self.cp_total}",
            f"Total pts: {self.pts_total}",
            f"Reinforcement Points: {self.reinf_points}",
            "+" * 75,
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
            for x in roster.iter(tag=self.PREFIX + 'costLimits')
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

        forces = (x for x in roster.forces.getchildren() if x.tag.removeprefix(self.PREFIX) == "force")
        self.forces = [ForceView(x) for x in forces]


if __name__ == '__main__':
    filename = "data/Harlequins_500.rosz"
    result = RosterView(filename, True)
    print(result)
