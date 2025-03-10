import logging
import sys

def get_stdout_handler():
    stdout_handler = logging.StreamHandler(sys.stdout)
    return stdout_handler

def get_formatter():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    return formatter

def get_logger(name, handler=get_stdout_handler(), formatter=get_formatter()):
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
