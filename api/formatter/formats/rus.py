from .format_printer import DefaultPrinter
from ..rosterview import RosterView
from ..extensions import add_double_whitespaces


class RussianTournamentsPrinter(DefaultPrinter):
    force_header = "++"

    def print(self, roster: RosterView) -> str:
        header = ''.join([
            '+' * 50 + '\n',
            '+ Team: \n',
            '+ Player: \n',
            f"+ Army name: {roster.name}\n",
            '+ HIN: \n',
            f"+ Factions used: {', '.join(roster.factions)}\n",
            f"+ Total cost: {roster.pts_total} pts\n",
        ])

        if roster.options.show_secondaries:
            header += self._format_secondaries(roster, "+ ")

        header += "+" * 50 + "\n\n"

        forces = '\n'.join(self._print_force(x) for x in roster.forces)
        forces = forces.strip('\n')
        result = header + forces + '\n' + '+' * 50
        return add_double_whitespaces(result)
