import os
import glob
from yaml import load, FullLoader


class BasicSelectorChecker:
    def __init__(self):
        self.database = dict()

        # load general selections
        with open(os.path.join("formatter", "res", "basic_selections", "general.yml"), "r") as f:
            data = load(f, Loader=FullLoader)
            self.database['general'] = set(data)

        files = glob.glob(os.path.join("formatter", "res", "basic_selections", "*.yml"))
        files = set(files) - {os.path.join("formatter", "res", "basic_selections", "general.yml")}
        for file in files:
            with open(file, "r") as f:
                data = load(f, Loader=FullLoader)
                self.database[data['faction']] = data['selections']

    def is_basic(self, catalogue: str, holder_name: str, selection_name: str):
        # check in the general catalogue
        if selection_name in self.database.get('general', set()):
            return True

        # check in the exact catalogue
        if selection_name in self.database.get(catalogue, {}).get(holder_name, {}):
            return True

        # check if everything should be omitted here
        if "*" in self.database.get(catalogue, {}).get(holder_name, {}):
            return True

        # remove last dash-separated word iteratively and check again
        # it would allow constructing catalogues like
        # "Imperium",
        # "Imperium - Adeptus Astartes",
        # and "Imperium - Adeptus Astartes - Iron Hands"
        dash_separated = catalogue.split('-')
        while len(dash_separated) > 1:
            dash_separated = dash_separated[:-1]
            catalogue = '-'.join(dash_separated).strip()
            if (
                    selection_name in self.database.get(catalogue, {}).get(holder_name, {}) or
                    "*" in self.database.get(catalogue, {}).get(holder_name, {})
            ):
                return True

        return False
