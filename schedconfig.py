import os
import random

SECRET_KEY = "".join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)])

MORDRED_CONF = 'mordred/setup.cfg'
GIT_REPOS = os.environ.get('GIT_REPOS')

DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')

ELASTIC_USER = os.environ.get('ELASTIC_USER')
ELASTIC_PASS = os.environ.get('ELASTIC_PASS')
ELASTIC_HOST = os.environ.get('ELASTIC_HOST')
ELASTIC_PORT = os.environ.get('ELASTIC_PORT')

