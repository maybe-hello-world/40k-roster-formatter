from collections import Counter

from ..rosterview import RosterView
from ..forceview import ForceView
from ..extensions import add_double_whitespaces, number_of_units, count_secondaries
from ..utils import expand_cps, FormatterOptions


class DefaultPrinter:
    force_header = "=="
    unit_model_wrapper = "({0})"



    @staticmethod
    def _format_secondaries(roster: RosterView, prefix: str = "") -> str:
        secondaries = count_secondaries(roster)
        header = ""
        header += f"{prefix}\n"
        header += f"{prefix}Number of Units: {number_of_units(roster)}\n"
        header += f"{prefix}Assassination: {secondaries['assassination']} points\n"
        header += f"{prefix}Bring it Down: {secondaries['bring it down']} points\n"
        header += f"{prefix}No Prisoners: {secondaries['no prisoners']} points\n"
        header += f"{prefix}Abhor the Witch: {secondaries['abhor the witch']} points\n"
        return header

    def print(self, roster: RosterView) -> str:
        header = ''.join([
            f"Army name: {roster.name}\n",
            f"Factions used: {', '.join(roster.factions)}\n",
            "" if roster.army_of_renown is None else f"Army of Renown: {roster.army_of_renown}\n",
            f"Command Points: {expand_cps(roster.cp_modifiers)}={roster.cp_total}\n",
            f"Total cost: {roster.pts_total} pts, {roster.pl_total} PL\n",
            "" if roster.cabal_points is None else f"Cabal Points: {roster.cabal_points}\n",
            f"Reinforcement Points: {roster.reinf_points} pts\n",
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
        force.no_force_org = [force.options.selector_checker.clean_obligatory_selections(force, x) for x in force.no_force_org]
        force.supreme_commander = [force.options.selector_checker.clean_obligatory_selections(force, x) for x in force.supreme_commander]
        force.agents_of_imperium = [force.options.selector_checker.clean_obligatory_selections(force, x) for x in force.agents_of_imperium]
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

        faction = force.faction + " " if force.faction else ""
        header = f"{self.force_header} {faction}{force.detachment} {self.force_header}"
        if not force.options.remove_costs:
            header += f" {force.cp} CP, {force.pts} pts, {force.pl} PL"
        if force.cabal_points > 0:
            header += "," if not force.options.remove_costs else ""
            header += f" {force.cabal_points} Cabal Points"

        output += header + "\n\n"

        if force.stratagems:
            output += "Stratagems:\n"
            for x in force.stratagems:
                output += "- " + x + "\n"
            output += "\n"

        if force.no_force_org:
            output += "No Force Org Slot:\n"
            for x in force.no_force_org:
                output += "- " + self._print_unit(x, force.options) + "\n"
            output += "\n"

        if force.agents_of_imperium:
            output += "Agent of the Imperium:\n"
            for x in force.agents_of_imperium:
                output += "- " + self._print_unit(x, force.options) + "\n"
            output += "\n"

        if force.supreme_commander:
            output += "Primarch | Daemon Primarch | Supreme Commander:\n"
            for x in force.supreme_commander:
                output += self._print_unit(x, force.options) + "\n"
            output += "\n"

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
        output = ""
        output += f'[{costs.get("pts", "???")} pts, {costs.get("pl", "???")} PL'
        if (y := costs.get('cp', 0)) != 0:
            output += f', {y} CP'
        if (y := costs.get('cabal', 0)) != 0:
            output += f', {y} Cabal Points'
        output += ']'
        return output

    def _print_unit(self, unit: dict, options: FormatterOptions):
        output = ""
        if options.show_model_count:
            output += self.unit_model_wrapper.format(unit.get('models')) + " "

        output += unit.get('name', '<Unparsed Unit Name>')
        if selections := unit.get('children', []):
            output += ": "
            output += self._print_unit_selections(selections)
        output += " "

        if not options.remove_costs:
            output += self._format_costs(unit.get('cost', {}))

        return output

    @staticmethod
    def _print_unit_selections(selections: list) -> str:
        selections = sorted(selections, key=lambda x: x['name'])

        string_selections = []
        for selection in selections:
            result = ""
            if (number := selection.get('number', 1)) != 1:
                result = f"{number}x"
            result += selection.get('name', "<Unparsed Name>")
            if children := selection.get('children', []):
                result += f" ({DefaultPrinter._print_unit_selections(children)})"

            string_selections.append(result)

        # collapsing equivalent units:
        counter = Counter(string_selections)
        string_selections = [f"{'' if value == 1 else str(value) + 'x'}{key}" for key, value in counter.items()]
        return ', '.join(string_selections)
