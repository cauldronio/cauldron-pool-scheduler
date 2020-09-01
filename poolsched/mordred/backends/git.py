import logging
import json
import traceback

import sqlalchemy
from sirmordred.config import Config
from sirmordred.task_projects import TaskProjects
from sirmordred.task_collection import TaskRawDataCollection
from sirmordred.task_enrich import TaskEnrich


from .base import Backend


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("worker")

PROJECTS_FILE = 'mordred/projects.json'
CONFIG_PATH = 'mordred/setup.cfg'
BACKEND_SECTION = 'git'


class GitRaw(Backend):
    def __init__(self, **kwargs):
        super().__init__()
        self.url = kwargs['url']
        self.clone_path = kwargs['clone_path']

    def create_projects_file(self):
        """Create the projects.json for Grimoirelab"""
        logger.info("Creating projects.json for GitRaw repository {}".format(self.url))
        projects = {'Project': {BACKEND_SECTION: [self.url]}}
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)

    def create_config(self):
        """Create the configuration file"""
        self.config = Config(CONFIG_PATH)
        self.config.set_param(BACKEND_SECTION, 'git-path', self.clone_path)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def start_analysis(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error
        """
        TaskProjects(self.config).execute()
        print("==>\tStart raw data retrieval from Git")
        task = TaskRawDataCollection(self.config, backend_section=BACKEND_SECTION)
        try:
            out_repos = task.execute()
            repo = out_repos[0]
            if 'error' in repo and repo['error']:
                logger.error(repo['error'])
                return 1
        except Exception as e:
            logger.error("Error in raw data retrieval from Git. Cause: {}".format(e))
            traceback.print_exc()
            return 1


class GitEnrich(Backend):
    def __init__(self, **kwargs):
        super().__init__()
        self.url = kwargs['url']

    def create_projects_file(self):
        """Create the projects.json for Grimoirelab"""
        logger.info("Creating projects.json for GitEnrich repository {}".format(self.url))
        projects = {'Project': {'git': [self.url]}}
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)

    def create_config(self):
        """Create the configuration file"""
        self.config = Config(CONFIG_PATH)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def start_analysis(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error
        """
        TaskProjects(self.config).execute()
        print("==>\tStart enrichment for Git")
        task = None
        while not task:
            try:
                task = TaskEnrich(self.config, backend_section=BACKEND_SECTION)
            except sqlalchemy.exc.InternalError:
                # There is a race condition in the code
                task = None

        try:
            task.execute()
        except Exception as e:
            logger.warning("Error enriching data for Git. Cause: {}".format(e))
            traceback.print_exc()
            return 1
