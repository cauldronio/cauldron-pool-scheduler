import logging
import configparser

from django.conf import settings

logger = logging.getLogger("mordred-worker")


class Backend:
    mordred_file = 'mordred/setup.cfg'

    def create_config(self):
        """Create the configuration files"""
        raise NotImplementedError

    def start_analysis(self):
        """Call to Grimoirelab"""
        raise NotImplementedError

    def basic_setup(self):
        url = 'https://admin:{}@{}:{}'.format(settings.ES_ADMIN_PASSWORD,
                                              settings.ES_IN_HOST,
                                              settings.ES_IN_PORT)
        config = configparser.ConfigParser()
        with open(self.mordred_file, 'r') as f:
            config.read_file(f)
        config['es_collection']['url'] = url
        config['es_enrichment']['url'] = url
        config['git']['git-path'] = settings.GIT_REPOS
        with open(self.mordred_file, 'w+') as f:
            config.write(f)

    def run(self):
        self.basic_setup()
        self.create_config()
        return self.start_analysis()
