import logging
import json
import math
import traceback
import sqlalchemy

from sirmordred.config import Config
from sirmordred.task_projects import TaskProjects
from sirmordred.task_collection import TaskRawDataCollection
from sirmordred.task_enrich import TaskEnrich

from .base import Backend


logger = logging.getLogger(__name__)

PROJECTS_FILE = 'tmp_projects.json'
BACKEND_SECTIONS = ['gitlab:issue', 'gitlab:merge']


class GitLabRaw(Backend):
    def __init__(self, **kwargs):
        self.config = None
        self.url = kwargs['url']
        self.token = kwargs['token']

    def create_config(self):
        """Create the configuration files"""
        logger.info("Creating configuration for Grimoirelab")
        projects = {'Project': {}}
        for section in BACKEND_SECTIONS:
            projects['Project'][section] = [self.url]

        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)

        self.config = Config(self.mordred_file)
        for section in BACKEND_SECTIONS:
            self.config.set_param(section, 'api-token', self.token)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def start_analysis(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error, other for time to reset in minutes
        """
        TaskProjects(self.config).execute()
        for section in BACKEND_SECTIONS:
            task = TaskRawDataCollection(self.config, backend_section=section)

            try:
                out_repos = task.execute()
                repo = out_repos[0]
                if 'error' in repo and repo['error']:
                    logger.error(repo['error'])
                    if repo['error'].startswith('RateLimitError'):
                        seconds_to_reset = float(repo['error'].split(' ')[-1])
                        restart_minutes = math.ceil(seconds_to_reset/60) + 2
                        logger.warning("RateLimitError. This task will be restarted in: "
                                       "{} minutes".format(restart_minutes))
                        return restart_minutes

            except Exception as e:
                logger.error("Error in raw data retrieval from {}. Cause: {}".format(section, e))
                traceback.print_exc()
                return 1


class GitLabEnrich(Backend):
    def __init__(self, **kwargs):
        self.config = None
        self.url = kwargs['url']

    def create_config(self):
        """Create the configuration files"""
        logger.info("Creating configuration for Grimoirelab")
        projects = {'Project': {}}
        for section in BACKEND_SECTIONS:
            projects['Project'][section] = [self.url]
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)

        self.config = Config(self.mordred_file)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def start_analysis(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error
        """
        TaskProjects(self.config).execute()
        for section in BACKEND_SECTIONS:
            task = None
            while not task:
                try:
                    task = TaskEnrich(self.config, backend_section=section)
                except sqlalchemy.exc.InternalError:
                    # There is a race condition in the code
                    task = None

            try:
                task.execute()
            except Exception as e:
                logger.warning("Error enriching data for {}. Cause: {}".format(section, e))
                traceback.print_exc()
                return 1
