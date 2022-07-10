from .format_printer import DefaultPrinter
from ..rosterview import RosterView
from ..forceview import ForceView


class WTCPrinter(DefaultPrinter):
    @staticmethod
    def print(roster: RosterView) -> str:
        return 'wtc'
