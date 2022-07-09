from .format_printer import FormatPrinter
from ..rosterview import RosterView
from ..forceview import ForceView
from ..extensions import add_double_whitespaces
from ..utils import expand_cps


class DefaultPrinter(FormatPrinter):
    @staticmethod
    def print(roster: RosterView) -> str:
        header = ''.join([
            f"Army name: {roster.name}\n",
            f"Factions used: {', '.join(roster.factions)}\n",
            "" if roster.army_of_renown is None else f"Army of Renown: {roster.army_of_renown}\n",
            f"Command Points: {expand_cps(roster.cp_modifiers)}={roster.cp_total}\n",
            f"Total cost: {roster.pts_total} pts, {roster.pl_total} PL\n",
            "" if roster.cabal_points is None else f"Cabal Points: {roster.cabal_points}\n",
            f"Reinforcement Points: {roster.reinf_points} pts\n",
            "+" * 20 + '\n',
            "\n",
        ])

        forces = '\n'.join(DefaultPrinter.print_force(x) for x in roster.forces)

        result = header + forces
        return add_double_whitespaces(result)

    @staticmethod
    def print_force(force: ForceView):
        return str(force)
