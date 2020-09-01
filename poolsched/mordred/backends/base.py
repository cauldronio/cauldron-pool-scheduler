import logging

CONFIG_PATH = 'mordred/setup.cfg'
JSON_DIR_PATH = 'projects_json'

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("mordred-worker")


class Backend:
    def __init__(self, **kwargs):
        self.config = None

    def create_config(self):
        """Create the configuration file,
        specific for each backend"""
        raise NotImplementedError

    def create_projects_file(self):
        """Create the projects.json for Grimoirelab,
        specific for each backend"""
        raise NotImplementedError

    def start_analysis(self):
        """Call to Grimoirelab,
        specific for each backend"""
        raise NotImplementedError

    def run(self):
        self.create_projects_file()
        cfg = self.create_config()
        self.start_analysis()
