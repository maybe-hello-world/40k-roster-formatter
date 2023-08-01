from .gw_printer import GWPrinter
from ..rosterview import RosterView
from ..extensions import add_double_whitespaces


class WTCPrinter(GWPrinter):
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

        if roster.options.show_secondaries:
            header += self._format_secondaries(roster, "")

        header += self.roster_header * self.roster_header_length + "\n\n"

        forces = '\n'.join(self._print_force(x) for x in roster.forces)
        forces = forces.strip('\n')
        result = header + forces + '\n\n' + 'END OF ROSTER'
        return add_double_whitespaces(result)
