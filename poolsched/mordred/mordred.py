import sys
import os
import logging
import argparse
import traceback
import configparser

from backends.git import GitRaw, GitEnrich
from backends.github import GitHubRaw, GitHubEnrich
from backends.gitlab import GitLabRaw, GitLabEnrich
from backends.meetup import MeetupRaw, MeetupEnrich

CONFIG_PATH = 'mordred/setup.cfg'

LOG_LEVEL = os.getenv('LOG_LEVEL', '')
ES_USER = os.getenv('ELASTIC_USER', 'admin')
ES_PASS = os.getenv('ELASTIC_PASSWORD', '')
ES_HOST = os.getenv('ELASTIC_HOST', '')
ES_PORT = os.getenv('ELASTIC_PORT', '9200')

CONNECTORS = {
    'git': {
        'raw': GitRaw,
        'enrich': GitEnrich
    },
    'github': {
        'raw': GitHubRaw,
        'enrich': GitHubEnrich
    },
    'gitlab': {
        'raw': GitLabRaw,
        'enrich': GitLabEnrich
    },
    'meetup': {
        'raw': MeetupRaw,
        'enrich': MeetupEnrich
    }
}

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("worker")


def config_logging():
    """Config logging level output"""
    logging_levels = {
        'CRITICAL': logging.CRITICAL,
        'FATAL': logging.FATAL,
        'ERROR': logging.ERROR,
        'WARN': logging.WARNING,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG
    }
    level = logging_levels.get(LOG_LEVEL, logging.WARNING)
    logger.setLevel(level)


def get_params():
    """Get params to execute mordred"""
    parser = argparse.ArgumentParser(description="Run mordred for a repository")
    parser.add_argument('--backend', type=str, help='Backend to analyze')
    parser.add_argument('--phase', type=str, help='Phase (raw or enrich)')
    parser.add_argument('--url', type=str, help='URL repository to analyze')
    parser.add_argument('--token', type=str, help='token for the analysis', default="")
    parser.add_argument('--git-path', dest='git_path', type=str,
                        help='path where the Git repository will be cloned', default=None)
    return parser.parse_args()


def get_connector(backend, phase):
    try:
        return CONNECTORS[backend][phase]
    except KeyError:
        return None


def update_base_setup():
    url = 'https://{}:{}@{}:{}'.format(ES_USER, ES_PASS, ES_HOST, ES_PORT)
    config = configparser.ConfigParser()
    with open(CONFIG_PATH, 'r') as f:
        config.read_file(f)
    config['es_collection']['url'] = url
    config['es_enrichment']['url'] = url
    with open(CONFIG_PATH, 'w+') as f:
        config.write(f)


if __name__ == '__main__':
    args = get_params()
    config_logging()
    update_base_setup()

    Backend = get_connector(args.backend, args.phase)
    if not Backend:
        logger.error('Tuple ({},{}) not available'.format(args.backend, args.phase))
        sys.exit(1)

    backend = Backend(url=args.url, token=args.token, clone_path=args.git_path)

    try:
        out = backend.run()
        if out:
            sys.exit(out)
    except Exception:
        logger.error("Finished with errors")
        traceback.print_exc()
        sys.exit(1)
