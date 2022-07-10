from .format_printer import DefaultPrinter
from ..rosterview import RosterView
from ..extensions import add_double_whitespaces
from ..utils import expand_cps


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
            "" if roster.army_of_renown is None else f"+ Army of Renown: {roster.army_of_renown}\n",
            f"+ Total cost: {roster.pts_total} pts, {roster.pl_total} PL\n",
            f"+ Command Points: {expand_cps(roster.cp_modifiers)}={roster.cp_total}\n",
            "" if roster.cabal_points is None else f"+ Cabal Points: {roster.cabal_points}\n",
            f"+ Reinforcement Points: {roster.reinf_points} pts\n",
            "+" * 50 + '\n',
            "\n",
        ])

        forces = '\n'.join(self._print_force(x) for x in roster.forces)
        forces = forces.strip('\n')
        result = header + forces + '\n' + '+' * 50
        return add_double_whitespaces(result)
