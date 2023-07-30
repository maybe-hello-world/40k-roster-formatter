import logging

from .format_printer import DefaultPrinter
from ..forceview import ForceView
from ..rosterview import RosterView
from ..extensions import add_double_whitespaces, FormatterOptions


class WTCPrinter(DefaultPrinter):
    force_header = "=="
    roster_header = "+"
    roster_header_length = 60
    unit_model_wrapper = "{0}"

    def print(self, roster: RosterView) -> str:
        header = ''.join([
            self.roster_header * self.roster_header_length + '\n',
            'Player Name: \n',
            'Team Name: \n',
            f"Factions used: {', '.join(roster.factions)}\n",
            f"Army Points: {roster.pts_total}\n",
            f"Army Enhancements:\n"
            f"Detachment Rules: {roster.forces[0].detachment_choice}\n"
        ])

        header += self.roster_header * self.roster_header_length + "\n\n"

        forces = '\n'.join(self._print_force(x) for x in roster.forces)
        forces = forces.strip('\n')
        result = header + forces + '\n\n' + 'END OF ROSTER'
        return add_double_whitespaces(result)

    def _print_force(self, force: ForceView):
        if force.options.hide_basic_selections:
            force = self._clean_obligatory_selections(force)

        output = ""

        header = f"{self.force_header} {force.detachment_choice} {force.detachment}"
        if not force.options.remove_costs:
            header += f" [{force.pts} pts]"
        header += f" {self.force_header}"
        output += header + "\n\n"

        for key, value in force.enumerated_unit_categories.items():
            result = []
            if not value[1]:
                # no units of this category
                continue

            units = sorted(value[1], key=lambda y: y.get('name', 'A'))
            for i, unit in enumerate(units):
                result.append(f"{value[0]}: " + self._print_unit(unit, force.options) + "\n")

            output += ''.join(result) + '\n'
        return output

    @staticmethod
    def _format_costs(costs: dict) -> str:
        if costs.get('pts', None) is None:
            logging.warning("Costs are missing for one or more units.", extra={'costs': costs})
        return f'[{costs.get("pts", "???")} pts]'

    def _print_unit(self, unit: dict, options: FormatterOptions):
        output = ""
        if options.show_model_count:
            if unit.get('models', 0) > 1:
                output += self.unit_model_wrapper.format(unit.get('models')) + " "

        name = unit.get('name', None)
        if name is None:
            logging.warning("Unit name is missing.", extra={'unit': unit})
            name = '<Unparsed Unit Name>'
        output += name + " "
        if not options.remove_costs:
            output += f'[{unit.get("cost", "???")} pts]'
        if selections := unit.get('children', []):
            output += " "
            output += self._print_unit_selections(selections)
        return output
