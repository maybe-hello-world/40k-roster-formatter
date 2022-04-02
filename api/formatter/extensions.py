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

    def is_basic(self, faction: str, holder_name: str, selection_name: str):
        return (
                selection_name in self.database.get('general', {}) or
                selection_name in self.database.get(faction, {}).get(holder_name, {})
        )
