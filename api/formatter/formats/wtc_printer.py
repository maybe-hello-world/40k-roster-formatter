from .format_printer import DefaultPrinter
from ..forceview import ForceView
from ..rosterview import RosterView
from ..extensions import add_double_whitespaces, number_of_units, FormatterOptions
from ..utils import secondaries_suffix


class WTCPrinter(DefaultPrinter):
    force_header = "=="
    unit_model_wrapper = "{0}"

    def print(self, roster: RosterView) -> str:

        secondaries = roster.secondaries
        ass = secondaries['assassination']
        bid = secondaries['bring it down']
        nop = secondaries['no prisoners']
        atw = secondaries['abhor the witch']
        suffix = secondaries_suffix(roster.options.cap_secondaries)

        stratagems = []
        for force in roster.forces:
            stratagems.extend(force.stratagems)

        header = ''.join([
            '+' * 70 + '\n',
            'Player #: \n',
            'Team: \n',
            f"Factions used: {', '.join(roster.factions)}\n",
            "" if roster.army_of_renown is None else f"Army of Renown: {roster.army_of_renown}\n",
            f"Army points: {roster.pts_total}\n",
            f"Reinforcement Points: {roster.reinf_points} pts\n",
            f"Number of Units / Killpoints: {number_of_units(roster)}\n",
            f"Pre Game Stratagems: {', '.join(stratagems)}\n",
            f"Starting Command Points: {roster.cp_total}\n",
            "Warlord: \n",
            "Army Trait: \n",
            "Secondary Objectives Information\n",
            f"Assassination: {ass}" + suffix(ass),
            f"Bring it Down: {bid}" + suffix(bid),
            f"No Prisoners: {nop}" + suffix(nop),
            f"Abhor the Witch: {atw}" + suffix(atw),
        ])

        header += "+" * 70 + "\n\n"

        forces = '\n'.join(self._print_force(x) for x in roster.forces)
        forces = forces.strip('\n')
        result = header + forces + '\n\n' + 'END OF ROSTER'
        return add_double_whitespaces(result)

    def _print_force(self, force: ForceView):
        if force.options.hide_basic_selections:
            force = self._clean_obligatory_selections(force)

        output = ""

        faction = force.faction + " " if force.faction else ""
        header = f"{self.force_header} {faction}{force.detachment} ="
        if not force.options.remove_costs:
            cp = "+" + str(force.cp) if force.cp > 0 else str(force.cp)
            header += f" {cp} CP, [{force.pl} PL, {force.pts} pts]"
        header += f" {self.force_header}"

        output += header + "\n\n"

        if force.agents_of_imperium:
            output += "Agent of the Imperium:\n"
            for x in force.agents_of_imperium:
                output += "- " + self._print_unit(x, force.options) + "\n"
            output += "\n"

        if force.supreme_commander:
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
                result.append(f"{value[0]}: " + self._print_unit(unit, force.options) + "\n")

            output += ''.join(result) + '\n'

        if force.no_force_org:
            for x in force.no_force_org:
                output += "NFO: " + self._print_unit(x, force.options) + "\n"
            output += "\n"
        return output

    @staticmethod
    def _format_costs(costs: dict) -> str:
        return f'[{costs.get("pl", "???")} PL, {costs.get("pts", "???")} pts]'

    def _print_unit(self, unit: dict, options: FormatterOptions):
        output = ""
        if options.show_model_count:
            if unit.get('models', 0) > 1:
                output += self.unit_model_wrapper.format(unit.get('models')) + " "

        output += unit.get('name', '<Unparsed Unit Name>') + " "
        if not options.remove_costs:
            output += self._format_costs(unit.get('cost', {}))
        if selections := unit.get('children', []):
            output += " "
            output += self._print_unit_selections(selections)
        return output
