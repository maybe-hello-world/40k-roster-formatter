import logging
from collections import Counter

from .format_printer import DefaultPrinter
from ..forceview import ForceView
from ..rosterview import RosterView
from ..extensions import add_double_whitespaces, FormatterOptions

class GWPrinter(DefaultPrinter):
    roster_header = "+"
    roster_header_length = 60

    def print(self, roster: RosterView) -> str:
        header = ''.join([
            self.roster_header * self.roster_header_length + '\n',
            f"Army name: {roster.name}\n",
            f"Factions used: {', '.join(roster.factions)}\n",
            f"Army Points: {roster.pts_total}\n",
            f"Army Enhancements:\n"
            f"Detachment Rules: {roster.forces[0].detachment_choice}\n"
        ])

        header += self.roster_header * self.roster_header_length + "\n\n"

        forces = '\n'.join(self._print_force(x) for x in roster.forces)
        forces = forces.strip('\n')
        result = header + forces
        return add_double_whitespaces(result)

    def _print_force(self, force: ForceView):
        if force.options.hide_basic_selections:
            force = self._clean_obligatory_selections(force)

        output = ""

        # print epic heroes and characters
        epic_heroes = force.enumerated_unit_categories.get('Epic Hero', [[], []])[1]
        epic_heroes = sorted(epic_heroes, key=lambda y: y.get('name', 'A'))
        characters = force.enumerated_unit_categories.get('Character', [[], []])[1]
        characters = sorted(characters, key=lambda y: y.get('name', 'A'))

        if epic_heroes or characters:
            output += "CHARACTERS\n\n"
            for unit in epic_heroes + characters:
                output += self._print_unit(unit, force.options) + "\n"

            output += "\n"

        # print battleline units
        battleline = force.enumerated_unit_categories.get('Battleline', [[], []])[1]
        battleline = sorted(battleline, key=lambda y: y.get('name', 'A'))
        if battleline:
            output += "BATTLELINE\n\n"
            for unit in battleline:
                output += self._print_unit(unit, force.options) + "\n"

        # print others
        output += "OTHER DATASHEETS\n\n"
        for key, value in force.enumerated_unit_categories.items():
            if key in ['Epic Hero', 'Character', 'Battleline']:
                continue
            result = []
            if not value[1]:
                # no units of this category
                continue

            units = sorted(value[1], key=lambda y: y.get('name', 'A'))
            for i, unit in enumerate(units):
                result.append(self._print_unit(unit, force.options) + "\n")

            output += ''.join(result)

        return output

    def _print_unit(self, unit: dict, options: FormatterOptions):
        output = ""

        name = unit.get('name', None)
        if name is None:
            name = '<Unparsed Unit Name>'
            logging.warning("Unit name not parsed", extra={'unit': unit})
        output += name
        if not options.remove_costs:
            output += f" ({unit.get('cost', 0)} pts)"
        output += "\n"

        if selections := unit.get('children', []):
            output += self._print_unit_selections(selections)
            output += "\n"

        return output

    def _print_unit_selections(self, selections: list, level: int = 1) -> str:
        selections = sorted(selections, key=lambda x: x['name'])

        string_selections = []
        for selection in selections:
            result = ""
            if (number := selection.get('number', 1)) != 1:
                result = f"{number}x"
            name = selection.get('name', None)
            if name is None:
                logging.warning("Unit selection name not parsed", extra={'selection': selection})
                name = "<Unparsed Name>"
            result += name
            if children := selection.get('children', []):
                result += f"\n{self._print_unit_selections(children, level+1)}"

            string_selections.append(result)

        # collapsing equivalent units:
        counter = Counter(string_selections)
        string_selections = [f"{'' if value == 1 else str(value) + 'x'}{key}" for key, value in counter.items()]

        if string_selections:
            string_selections[0] = "• " + string_selections[0]
        if len(string_selections) > 1:
            string_selections[1:] = ["  " + x for x in string_selections[1:]]
        string_selections = [f"{' ' * (level * 2)} {x}" for x in string_selections]
        return '\n'.join(string_selections)