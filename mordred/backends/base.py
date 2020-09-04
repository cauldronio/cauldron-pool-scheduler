import logging
import configparser

import schedconfig

logger = logging.getLogger("mordred-worker")


class Backend:
    mordred_file = schedconfig.MORDRED_CONF

    def create_config(self):
        """Create the configuration files"""
        raise NotImplementedError

    def start_analysis(self):
        """Call to Grimoirelab"""
        raise NotImplementedError

    def basic_setup(self):
        url = 'https://{}:{}@{}:{}'.format(schedconfig.ELASTIC_USER,
                                           schedconfig.ELASTIC_PASS,
                                           schedconfig.ELASTIC_HOST,
                                           schedconfig.ELASTIC_PORT)
        config = configparser.ConfigParser()
        with open(schedconfig.MORDRED_CONF, 'r') as f:
            config.read_file(f)
        config['es_collection']['url'] = url
        config['es_enrichment']['url'] = url
        with open(schedconfig.MORDRED_CONF, 'w+') as f:
            config.write(f)

    def run(self):
        self.basic_setup()
        self.create_config()
        return self.start_analysis()
