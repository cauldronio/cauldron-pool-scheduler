import logging
import json
import traceback
import sqlalchemy

try:
    from sirmordred.config import Config
    from sirmordred.task_projects import TaskProjects
    from sirmordred.task_collection import TaskRawDataCollection
    from sirmordred.task_enrich import TaskEnrich
except ImportError:
    from . import sirmordred_fake
    Config = sirmordred_fake.Config
    TaskProjects = sirmordred_fake.TaskProjects
    TaskRawDataCollection = sirmordred_fake.TaskRawDataCollection
    TaskEnrich = sirmordred_fake.TaskEnrich

from .base import Backend


logger = logging.getLogger(__name__)

PROJECTS_FILE = 'tmp_projects.json'
BACKEND_SECTION = 'git'


class GitRaw(Backend):
    def __init__(self, url):
        self.config = None
        self.url = url

    def create_config(self):
        """Create the configuration files"""
        logger.info("Creating configuration for Grimoirelab")
        self.config = Config(self.mordred_file)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)
        projects = {'Project': {BACKEND_SECTION: [self.url]}}
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)

    def start_analysis(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error
        """
        TaskProjects(self.config).execute()
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
    def __init__(self, url):
        self.config = None
        self.url = url

    def create_config(self):
        """Create the configuration files"""
        logger.info("Creating configuration for Grimoirelab")
        self.config = Config(self.mordred_file)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)
        projects = {'Project': {'git': [self.url]}}
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)

    def start_analysis(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error
        """
        TaskProjects(self.config).execute()
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
