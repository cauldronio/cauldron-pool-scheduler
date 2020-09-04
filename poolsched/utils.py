import logging
import time


def file_formatter(filename):
    fmt = "[%(asctime)s - %(levelname)s - %(name)s] - %(message)s"
    formatter = logging.Formatter(fmt)
    formatter.converter = time.gmtime
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    return fh


def mordred_not_imported(*args, **kwargs):
    raise Exception("Mordred was not imported. There was a previous exception.")
