from .format_printer import FormatPrinter
from ..rosterview import RosterView
from ..forceview import ForceView


class WTCPrinter(FormatPrinter):
    @staticmethod
    def print(roster: RosterView) -> str:
        return 'wtc'
