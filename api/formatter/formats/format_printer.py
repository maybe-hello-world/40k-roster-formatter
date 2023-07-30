import logging
from collections import Counter

from ..rosterview import RosterView
from ..forceview import ForceView
from ..extensions import add_double_whitespaces, number_of_units, FormatterOptions


class DefaultPrinter:
    force_header = "=="
    unit_model_wrapper = "({0})"

    @staticmethod
    def _format_secondaries(roster: RosterView, prefix: str = "") -> str:
        secondaries = roster.secondaries
        ass = secondaries['assassination']
        bid = secondaries['bring it down']

        header = ""
        header += f"{prefix}\n"
        header += f"{prefix}Number of Units: {number_of_units(roster)}\n"
        header += f"{prefix}Character Units (Models): {ass[0]} ({ass[1]}) \n"
        header += f"{prefix}Vehicle/Monster Models (Max Points): {bid[0]} ({bid[1]}) \n"
        return header

    def print(self, roster: RosterView) -> str:
        header = ''.join([
            f"Army name: {roster.name}\n",
            f"Factions used: {', '.join(roster.factions)}\n",
            f"Total cost: {roster.pts_total} pts\n",
        ])

        if roster.options.show_secondaries:
            header += self._format_secondaries(roster)

        header += "+" * 50 + '\n\n'

        forces = ''.join(self._print_force(x) for x in roster.forces)
        forces = forces.strip('\n')

        result = header + forces
        return add_double_whitespaces(result)

    @staticmethod
    def _clean_obligatory_selections(force: ForceView) -> ForceView:
        for key, value in force.enumerated_unit_categories.items():
            force.enumerated_unit_categories[key] = [
                value[0],
                [force.options.selector_checker.clean_obligatory_selections(force, x) for x in value[1]]
            ]

        return force

    def _print_force(self, force: ForceView):
        if force.options.hide_basic_selections:
            force = self._clean_obligatory_selections(force)

        output = ""
        header = f"{self.force_header} {force.detachment_choice} {force.detachment} "
        if not force.options.remove_costs:
            header += f"{force.pts} pts "
        header += f"{self.force_header}"

        output += header + "\n\n"

        for key, value in force.enumerated_unit_categories.items():
            result = []
            if not value[1]:
                # no units of this category
                continue

            units = sorted(value[1], key=lambda y: y.get('name', 'A'))
            for i, unit in enumerate(units):
                result.append(f"{value[0]}{i + 1}: " + self._print_unit(unit, force.options) + "\n")

            output += ''.join(result) + '\n'

        return output

    @staticmethod
    def _format_costs(costs: dict) -> str:
        total_pts = costs.get('pts', "???")
        if total_pts == "???":
            logging.warning("Incomplete cost information", extra={'costs': costs})

        return f"[{total_pts} pts]"

    def _print_unit(self, unit: dict, options: FormatterOptions):
        output = ""
        if options.show_model_count:
            output += self.unit_model_wrapper.format(unit.get('models')) + " "

        name = unit.get('name', None)
        if name is None:
            name = '<Unparsed Unit Name>'
            logging.warning("Unit name not parsed", extra={'unit': unit})
        output += name
        if selections := unit.get('children', []):
            output += ": "
            output += self._print_unit_selections(selections)
        output += " "

        if not options.remove_costs:
            output += f"[{unit.get('cost', 0)} pts]"

        return output

    @staticmethod
    def _print_unit_selections(selections: list) -> str:
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
                result += f" ({DefaultPrinter._print_unit_selections(children)})"

            string_selections.append(result)

        # collapsing equivalent units:
        counter = Counter(string_selections)
        string_selections = [f"{'' if value == 1 else str(value) + 'x'}{key}" for key, value in counter.items()]
        return ', '.join(string_selections)
