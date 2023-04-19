from __future__ import annotations

import logging

from .forceview import ForceView
from .utils import remove_prefix, FormatterException
from .extensions import FormatterOptions, count_secondaries

from lxml import objectify
from itertools import chain
from zipfile import ZipFile
from typing import Mapping
from sentry_sdk import capture_exception


class RosterView:
    @staticmethod
    def __extract(input_file, zipped: bool = True) -> dict:
        if zipped:
            input_file = ZipFile(input_file)
            return {name: input_file.read(name) for name in input_file.namelist()}
        else:
            return {"default": input_file.encode('utf-8')}

    @staticmethod
    def __read_xml(content: dict) -> objectify.ObjectifiedElement:
        if len(content) != 1:
            exception = FormatterException(f"Unknown structure of provided rosz archive. Content: {content.keys()}")
            capture_exception(exception)
            raise exception

        name: str = next(iter(content))
        roster: objectify.ObjectifiedElement = objectify.fromstring(content[name])

        return roster

    def __set_reinf_points(self, roster: objectify.ObjectifiedElement):
        pts_limit = [
            x.costLimit.get("value")
            for x in roster.iter(tag='{*}costLimits')
            if (x.find("costLimit") is not None or hasattr(x, "costLimit"))
            and x.costLimit.get("name", "") == "pts"
        ]
        pts_limit = int(float(pts_limit[0])) if pts_limit else 0
        reinf_points = pts_limit - self.pts_total
        self.reinf_points = str(reinf_points) if reinf_points > 0 else 'none'

    def __init__(self, file, zipped: bool = True, options: Mapping[str, str] = None):
        if not options:
            options = {}

        self.options = FormatterOptions(**options)
        roster = self.__read_xml(self.__extract(file, zipped))
        self.name = roster.attrib.get("name", "")

        total_cost = {
            x.attrib['name'].strip(): int(float(x.attrib['value']))
            for x in roster.costs.iterchildren()
        }
        self.cp_total = total_cost.get("CP", 0)
        self.pl_total = total_cost.get("PL", 0)
        self.pts_total = total_cost.get("pts", 0)
        self.cabal_points = total_cost.get("Cabal Points", None)
        self.__set_reinf_points(roster)
        self.factions = set(x.attrib.get("catalogueName", "<ERROR: UNPARSED>") for x in roster.forces.iterchildren())
        if "<ERROR: UNPARSED>" in self.factions:
            logging.error("Unknown faction in roster.", extra={"factions": self.factions})

        forces = (x for x in roster.forces.iterchildren(tag="{*}force"))
        self.forces = [ForceView(x, self.options) for x in forces]
        self.cp_modifiers = sorted(chain.from_iterable(x.cp_modifiers for x in self.forces), reverse=True)
        army_of_renown = [x.army_of_renown for x in self.forces if x.army_of_renown is not None]
        self.army_of_renown = army_of_renown[0] if army_of_renown else None
        if self.army_of_renown:
            self.army_of_renown = remove_prefix(self.army_of_renown, "Army of Renown - ")

        self.debug_info = ""
        self.secondaries = count_secondaries(self)
